"""Invariants that must hold for any valid configuration (T4.1.1).

20 random configurations are drawn around the baseline (rates, buffers, sub-lot size,
failures, minor stops, staffing, parallel AVI, schedule mix). For each, the run must complete
and conserve vials at every sampled instant, and every station unit's state time must add up to
the horizon exactly.
"""

from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from ffdt.config import apply_overrides, load_config
from ffdt.metrics import ledger as L
from ffdt.sim.line import Line

BASE = Path(__file__).resolve().parents[2] / "configs" / "baseline_line.yaml"
N_RANDOM = 20


@pytest.fixture(scope="module")
def base():
    return load_config(BASE)


def random_config(base, seed: int):
    rng = np.random.default_rng(seed)
    sublot = int(rng.choice([10, 50, 100]))
    patch = {}
    for st in base.stations:
        p = {"rate_vpm": float(rng.uniform(150, 400))}
        if st.failures:
            p["failures"] = {
                "mtbf_min": float(rng.uniform(200, 6000)),
                "mttr_mean_min": float(rng.uniform(5, 90)),
                "mttr_cv": float(rng.uniform(0.2, 1.2)),
            }
        if st.minor_stops and rng.random() < 0.7:
            p["minor_stops"] = {
                "mean_between_min": float(rng.uniform(10, 120)),
                "mean_duration_min": float(rng.uniform(0.5, 4)),
            }
        patch[st.name] = p
    patch["avi"]["count"] = int(rng.integers(1, 3))
    combos = [(p, f) for p in base.products for f in base.formats]
    schedule = []
    for _ in range(int(rng.integers(1, 5))):
        prod, fmt = combos[int(rng.integers(len(combos)))]
        schedule.append(
            {"product": prod, "format": fmt, "size_vials": int(rng.integers(500, 15_000))}
        )
    return apply_overrides(
        base,
        {
            "sublot_vials": sublot,
            "buffer_vials": sublot * int(rng.integers(10, 40)),
            "schedule": schedule,
            "staffing": {
                "operator": int(rng.integers(1, 5)),
                "mechanic": int(rng.integers(1, 3)),
                "inspector": int(rng.integers(1, 3)),
            },
            "changeovers": {"scale": float(rng.uniform(0.3, 1.5))},
            "station_overrides": patch,
        },
    )


@pytest.mark.parametrize("seed", range(N_RANDOM))
def test_random_config_conserves_vials_and_time(base, seed):
    cfg = random_config(base, seed)
    line = Line(cfg, root_seed=seed, replication=seed % 3)
    ok = []

    def monitor():
        yield line.env.timeout(0.0137)  # off the event grid (see test_line)
        while True:
            led = line.ledger
            ok.append(led.started == led.packed + led.scrapped + line.wip_vials())
            yield line.env.timeout(7.31)

    line.env.process(monitor())
    assert line.run(), "campaign did not complete"
    assert ok and all(ok)
    led = line.ledger
    assert led.started == cfg.total_vials == led.packed + led.scrapped
    assert line.wip_vials() == 0
    # state-time sums: every unit covers exactly [0, horizon], before and after the overlay
    run = line.export()
    raw = L.states_df(run)
    over = L.calendar_overlay(raw, run["off_shift"])
    for df in (raw, over):
        sums = df.groupby(["station", "unit"])["minutes"].sum()
        assert sums.to_numpy() == pytest.approx(run["horizon_min"], rel=1e-9)
    # intervals of a unit never overlap
    for _, g in raw.sort_values("start").groupby(["station", "unit"]):
        assert (g["start"].to_numpy()[1:] >= g["end"].to_numpy()[:-1] - 1e-9).all()


@pytest.mark.parametrize("seed", range(5))
def test_no_failure_throughput_equals_bottleneck_rate(base, seed):
    rng = np.random.default_rng(100 + seed)
    rates = {st.name: float(rng.uniform(150, 400)) for st in base.stations}
    cfg = apply_overrides(
        base,
        {
            "schedule": [{"product": "prod_a", "format": "vial_2r", "size_vials": 200_000}],
            "station_overrides": {n: {"rate_vpm": r} for n, r in rates.items()},
        },
    )
    line = Line(cfg, use_calendar=False, stochastic=False, changeovers=False, quality=False)
    assert line.run()
    last = cfg.stations[-1].name
    t = np.array([o[2] for o in line.log.outputs if o[0] == last])
    v = np.array([o[5] for o in line.log.outputs if o[0] == last])
    # steady output rate between first and last packed sub-lot (excludes pipeline fill)
    rate = v[1:].sum() / (t[-1] - t[0])
    assert rate == pytest.approx(min(rates.values()), rel=0.005)


def test_empty_schedule_is_rejected_by_validation(base):
    with pytest.raises(ValidationError):
        apply_overrides(base, {"schedule": []})


@pytest.mark.parametrize("size", [1, 99, 100, 150])
def test_single_small_batch(base, size):
    cfg = apply_overrides(
        base, {"schedule": [{"product": "prod_b", "format": "vial_10r", "size_vials": size}]}
    )
    line = Line(cfg, root_seed=size)
    assert line.run()
    led = line.ledger
    assert led.started == size == led.packed + led.scrapped
    assert not [e for e in line.log.events if e[1] == "changeover"]  # nothing to change to
    assert line.ledger.batches[0].release_min is not None

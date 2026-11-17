from pathlib import Path

import pytest
from simhelpers import state_minutes

from ffdt.config import apply_overrides, load_config
from ffdt.sim.line import Line

BASE = Path(__file__).resolve().parents[2] / "configs" / "baseline_line.yaml"


@pytest.fixture(scope="module")
def cfg():
    return load_config(BASE)


def test_baseline_week_completes_without_deadlock(cfg):
    line = Line(cfg, root_seed=1, replication=0)
    assert line.run()
    led = line.ledger
    assert led.started == cfg.total_vials == led.packed + led.scrapped
    assert 0 < led.scrapped < 0.02 * cfg.total_vials
    assert all(b.complete for b in line.ledger.batches)


def test_vial_conservation_at_all_times(cfg):
    small = apply_overrides(
        cfg,
        {
            "schedule": [
                {"product": "prod_a", "format": "vial_2r", "size_vials": 20_050},
                {"product": "prod_b", "format": "vial_10r", "size_vials": 15_000},
            ]
        },
    )
    line = Line(small, root_seed=2)
    checks = []

    def monitor():
        # sample off the event grid: within one SimPy instant a sub-lot can be between
        # processes (store.get fired, consumer not yet resumed); that is not observable time
        yield line.env.timeout(0.0123)
        while True:
            led = line.ledger
            checks.append(led.started == led.packed + led.scrapped + line.wip_vials())
            yield line.env.timeout(1.7071)

    line.env.process(monitor())
    assert line.run()
    assert len(checks) > 50 and all(checks)
    assert line.wip_vials() == 0


def test_deterministic_no_failure_line_runs_at_filler_rate(cfg):
    line = Line(cfg, use_calendar=False, stochastic=False, changeovers=False, quality=False)
    assert line.run()
    # filler is the slowest nominal rate (240 vpm); pipeline fill adds the 30 min tunnel
    # residence plus a few minutes of sub-lot transfer through the other stations
    ideal = cfg.total_vials / 240
    assert 30 < line.campaign_end_min - ideal < 35
    assert state_minutes(line.log, "filler")["RUN"] == pytest.approx(ideal)


def test_tunnel_backpressure_blocks_washer(cfg):
    slow_end = apply_overrides(cfg, {"station_overrides": {"cartoner": {"rate_vpm": 50}}})
    line = Line(slow_end, use_calendar=False, stochastic=False, changeovers=False, quality=False)
    line.run()
    assert state_minutes(line.log, "washer").get("BLOCKED", 0) > 0
    assert line.campaign_end_min == pytest.approx(cfg.total_vials / 50, rel=0.01)


def test_parallel_units_share_buffers(cfg):
    two = apply_overrides(cfg, {"station_overrides": {"avi": {"count": 2}}})
    line = Line(two, use_calendar=False, stochastic=False, changeovers=False, quality=False)
    assert line.run()
    assert {u for st, u, *_ in line.log.states if st == "avi"} == {0, 1}

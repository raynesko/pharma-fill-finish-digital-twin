from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ffdt.config import load_config
from ffdt.experiments import bottleneck as B

BASE = Path(__file__).resolve().parents[2] / "configs" / "baseline_line.yaml"


def _three_station(rates):
    """Synthetic 3-machine serial line (filler -> capper -> avi) with chosen nominal rates."""
    cfg = load_config(BASE)
    sts = [
        cfg.stations[i].model_copy(update={"rate_vpm": r})
        for i, r in zip((2, 3, 4), rates, strict=True)
    ]
    return type(cfg).model_validate(cfg.model_copy(update={"stations": sts}).model_dump())


@pytest.mark.parametrize("rates, known", [((300, 120, 300), "capper"), ((300, 300, 120), "avi")])
def test_synthetic_three_machine_line_known_bottleneck(rates, known):
    cfg = _three_station(rates)
    ev = pd.concat(
        [B.replication(cfg, 7, r, use_calendar=False, changeovers=False) for r in range(3)]
    ).reset_index()
    v = B.verdict(B.picks(ev))
    assert v["consensus"] == known
    for m in B.CORE:
        assert v[m] == known, m


def test_active_periods_require_all_parallel_units():
    s = pd.DataFrame(
        {
            "unit": [0, 0, 1, 1],
            "state": ["RUN", "STARVED", "RUN", "RUN"],
            "start": [0.0, 5.0, 2.0, 6.0],
            "end": [5.0, 10.0, 6.0, 10.0],
        }
    )
    assert B.active_periods(s, 2).tolist() == [[2.0, 5.0]]
    assert B.active_periods(s, 1).tolist() == [[0.0, 10.0]]


def test_active_period_sole_and_shifting_by_hand():
    # A active [0,10) then B active [8,20): A is longest until B's longer period takes over.
    periods = {"A": np.array([[0.0, 10.0]]), "B": np.array([[8.0, 20.0]])}
    sh = B.active_period_shares(periods, ppt_min=20.0)
    # A is bottleneck on [0,8), B on [8,20); overlap of A's and B's periods = [8,10) = 2 min
    assert sh.loc["A", "shifting_share"] == pytest.approx(2 / 20)
    assert sh.loc["B", "shifting_share"] == pytest.approx(2 / 20)
    assert sh.loc["A", "sole_share"] == pytest.approx(8 / 20)
    assert sh.loc["B", "sole_share"] == pytest.approx(10 / 20)


def test_arrow_method_points_to_middle():
    st = pd.Series({"a": 0.01, "b": 0.02, "c": 0.30})
    bl = pd.Series({"a": 0.40, "b": 0.05, "c": 0.0})
    chosen, cands = B.arrow_method(st, bl)
    assert chosen == "b" and cands == ["b"]


def test_active_period_overlaps_on_both_sides_are_not_double_counted():
    # A [0,10) -> B [5,20) -> C [8,40). B overlaps A on [5,10) and C on [8,20): union [5,20).
    periods = {
        "A": np.array([[0.0, 10.0]]),
        "B": np.array([[5.0, 20.0]]),
        "C": np.array([[8.0, 40.0]]),
    }
    sh = B.active_period_shares(periods, ppt_min=40.0) * 40
    assert sh.loc["B", "shifting_share"] == pytest.approx(15)
    assert sh.loc["B", "sole_share"] == pytest.approx(0)
    assert (sh.loc["A", "sole_share"], sh.loc["A", "shifting_share"]) == pytest.approx((5, 5))
    assert (sh.loc["C", "sole_share"], sh.loc["C", "shifting_share"]) == pytest.approx((20, 12))


def test_run_level_methods_agree_with_full_evidence_on_baseline_tables():
    """The app's fast run-level methods pick the same station as the full analysis."""
    base = Path(__file__).resolve().parents[2] / "results" / "baseline"
    if not (base / "baseline.stations.parquet").exists():
        pytest.skip("scenario results not generated (python tasks.py scenarios)")
    st = pd.read_parquet(base / "baseline.stations.parquet")
    q = pd.read_parquet(base / "baseline.queues.parquet")
    v = B.run_level_verdict(B.run_level_picks(st, q))
    assert v["consensus"] == "filler" and v["methods_agreeing"] == 3


def test_run_level_picks_on_synthetic_line():
    cfg = _three_station((300, 120, 300))
    from ffdt.experiments import runner

    res = runner.run(cfg, n_reps=2, seed=3)
    v = B.run_level_verdict(B.run_level_picks(res.stations, res.queues))
    assert v["consensus"] == "capper"

import numpy as np
import pandas as pd
import pytest

from ffdt.experiments import baseline_report as B


def _stations(n=5):
    rng = np.random.default_rng(0)
    rows = []
    for r in range(n):
        for st, rate in (("a", 300.0), ("b", 200.0)):
            mins = dict(zip(B.STATES, rng.uniform(10, 100, len(B.STATES)), strict=True))
            ppt = sum(mins.values())
            rows.append(
                {
                    "station": st,
                    "rate_vpm": rate,
                    "ppt_min": ppt,
                    "replication": r,
                    "utilization": mins["RUN"] / ppt,
                    "A": 0.9,
                    "P": 0.8,
                    "Q": 1.0,
                    "OEE": 0.72,
                }
                | {f"{k}_min": v for k, v in mins.items()}
            )
    return pd.DataFrame(rows)


def test_state_shares_sum_to_one():
    sh = B.state_shares(_stations())
    assert sh.sum(axis=1).to_numpy() == pytest.approx([1.0, 1.0])
    assert list(sh.index) == ["a", "b"]  # line order kept


def test_station_ci_brackets_mean_and_is_degenerate_for_constants():
    t = B.station_oee_table(_stations())
    assert (t["A_ci_low"] <= t["A"]).all() and (t["A"] <= t["A_ci_high"]).all()
    assert t.loc["a", "OEE_ci_high"] == pytest.approx(0.72)


def test_bottleneck_evidence_has_no_offline_station_and_matches_queue():
    st = _stations()
    st = pd.concat([st, st.assign(station="manual_inspection")])
    q = pd.DataFrame({"buffer": ["in:a", "in:b"] * 2, "mean_sublots": [1.0, 5.0, 3.0, 7.0]})
    ev = B.bottleneck_evidence(st, q)
    assert "manual_inspection" not in ev.index
    assert ev.loc["b", "mean_queue_in_front_sublots"] == pytest.approx(6.0)

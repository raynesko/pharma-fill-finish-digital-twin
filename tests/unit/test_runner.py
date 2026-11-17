from pathlib import Path

import pandas as pd
import pytest

from ffdt.config import apply_overrides, load_config
from ffdt.experiments import runner
from ffdt.sim.line import Line

BASE = Path(__file__).resolve().parents[2] / "configs" / "baseline_line.yaml"
SMALL = [
    {"product": "prod_a", "format": "vial_2r", "size_vials": 30_000},
    {"product": "prod_b", "format": "vial_10r", "size_vials": 30_000},
]


@pytest.fixture(scope="module")
def cfg():
    return apply_overrides(load_config(BASE), {"schedule": SMALL})


def test_parallel_equals_serial(cfg):
    a = runner.run(cfg, n_reps=3, seed=5, n_jobs=1)
    b = runner.run(cfg, n_reps=3, seed=5, n_jobs=2)
    pd.testing.assert_frame_equal(a.summary, b.summary)
    pd.testing.assert_frame_equal(a.stations, b.stations)
    pd.testing.assert_frame_equal(a.pareto, b.pareto)
    pd.testing.assert_frame_equal(a.queues, b.queues)
    assert a.summary["replication"].tolist() == [0, 1, 2]
    assert a.summary["line_oee"].nunique() == 3  # replications differ


def test_parquet_carries_config_hash_and_git_sha(cfg, tmp_path):
    res = runner.run(cfg, n_reps=2, seed=5)
    files = runner.write_parquet(res, tmp_path / "base.parquet")
    assert {f.name for f in files} == {
        "base.summary.parquet",
        "base.stations.parquet",
        "base.pareto.parquet",
        "base.queues.parquet",
    }
    for f in files:
        meta = runner.read_metadata(f)
        assert meta["ffdt.config_hash"] == cfg.hash()
        assert meta["ffdt.git_sha"]  # a SHA, SHA+dirty, or "no-git" before the first commit
        assert meta["ffdt.seed"] == "5" and meta["ffdt.n_reps"] == "2"
    back = pd.read_parquet(tmp_path / "base.summary.parquet")
    pd.testing.assert_frame_equal(back, res.summary)


def _first_draws(line):
    """Initial failure/minor-stop clocks of every station unit plus the first quality draws."""
    out = {f"{m.name}#{m.unit}": (m.clocks.ttf, m.clocks.ttm) for m in line.machines if m.clocks}
    q = line.quality
    out["quality"] = tuple(float(g.random()) for g in (q._fw, q._def, q._det, q._fr, q._conf))
    return out


def test_changing_one_station_leaves_other_streams_unchanged(cfg):
    changed = apply_overrides(
        cfg,
        {"station_overrides": {"capper": {"rate_vpm": 200, "minor_stops": None}}},
    )
    a = _first_draws(Line(cfg, root_seed=9, replication=3))
    b = _first_draws(Line(changed, root_seed=9, replication=3))
    capper_a = a.pop("capper#0")
    capper_b = b.pop("capper#0")
    assert a == b  # every other station and the quality model draw identical numbers
    assert capper_a[0] == capper_b[0]  # same failure stream; only the minor-stop clock is gone
    assert capper_b[1] == float("inf")


def test_adding_a_parallel_unit_does_not_change_other_streams(cfg):
    """Streams are keyed by name, not position: adding a parallel AVI unit leaves the others."""
    two = apply_overrides(cfg, {"station_overrides": {"avi": {"count": 2}}})
    a = _first_draws(Line(cfg, root_seed=9))
    b = _first_draws(Line(two, root_seed=9))
    assert "avi#1" in b
    b.pop("avi#1")
    assert a == b


def test_experiment_design_file_is_loaded():
    exp = runner.load_experiment()
    assert exp["seed"] == runner.DEFAULT_SEED
    assert exp["n_reps"] >= 10 and exp["mode"] == "terminating"

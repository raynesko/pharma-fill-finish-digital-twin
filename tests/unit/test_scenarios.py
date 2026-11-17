"""Scenario files validate and differ from baseline only where declared (T5.1.1, T5.1.2).
Nothing here runs a full scenario campaign."""

import pytest

from ffdt.experiments import scenarios as S
from ffdt.sim.line import Line

ALL = S.all_scenarios()
BASE = S.baseline_scenario().config


def test_matrix_has_required_scenarios():
    families = {s.family for s in ALL}
    assert {"SC-01", "SC-02", "SC-03", "SC-04", "SC-05"} <= families
    assert len(ALL) >= 6
    assert [s.name for s in ALL if s.exploratory] == ["sc05_combo_co50_avi2"]


@pytest.mark.parametrize("sc", ALL, ids=lambda s: s.name)
def test_every_scenario_validates_and_changes_something(sc):
    assert sc.config.hash() != BASE.hash()
    assert sc.config.total_vials == BASE.total_vials  # every scenario keeps the 600,000 vials
    assert sc.config.calendar == BASE.calendar and sc.config.quality == BASE.quality


def test_batch_scenarios_keep_mix_and_sequence():
    def mix(cfg):
        out = {}
        for b in cfg.schedule:
            out[(b.product, b.format)] = out.get((b.product, b.format), 0) + b.size_vials
        return out

    def runs(cfg):  # sequence of distinct consecutive setups
        seq = [(b.product, b.format) for b in cfg.schedule]
        return [s for i, s in enumerate(seq) if i == 0 or seq[i - 1] != s]

    by = {s.name: s.config for s in ALL}
    for name, n in (("sc02_batch_x0p5", 12), ("sc02_batch_x2", 4)):
        assert len(by[name].schedule) == n
        assert mix(by[name]) == mix(BASE) and runs(by[name]) == runs(BASE)


@pytest.mark.parametrize("sc", ALL, ids=lambda s: s.name)
def test_unchanged_stations_draw_identical_streams(sc):
    """Common random numbers: every station unit present in both configs gets the same first
    failure and minor-stop clocks, and the quality model the same first draws."""

    def draws(cfg):
        line = Line(cfg, root_seed=20261116, replication=7)
        d = {f"{m.name}#{m.unit}": (m.clocks.ttf, m.clocks.ttm) for m in line.machines if m.clocks}
        q = line.quality
        d["quality"] = tuple(float(g.random()) for g in (q._fw, q._def, q._det, q._fr))
        return d

    a, b = draws(BASE), draws(sc.config)
    for key in a.keys() & b.keys():
        assert a[key] == b[key], key


def test_name_must_match_file(tmp_path):
    p = tmp_path / "x.yaml"
    p.write_text(
        "name: y\ndescription: d\nfamily: F\nexploratory: false\noverrides: {}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="must match"):
        S.load(p)

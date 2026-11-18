import pytest

from ffdt.experiments import scenarios
from ffdt.experiments import sensitivity as S


@pytest.fixture(scope="module")
def cfgs():
    return {c["name"]: c for c in S.configs()}


@pytest.fixture(scope="module")
def base():
    return scenarios.baseline_scenario().config


def _diff(a, b, path=""):
    """Paths of leaf values that differ between two nested dumps."""
    if isinstance(a, dict):
        return [p for k in a for p in _diff(a[k], b[k], f"{path}.{k}")]
    if isinstance(a, list):
        return [
            p
            for i, (x, y) in enumerate(zip(a, b, strict=True))
            for p in _diff(x, y, f"{path}[{i}]")
        ]
    return [] if a == b else [path]


def test_twelve_parameters_two_levels_each(cfgs):
    assert len(cfgs) == 24
    assert len({c["param"] for c in cfgs.values()}) == 12


@pytest.mark.parametrize(
    "name, expected",
    [
        ("filler_rate@0.8", {".stations[2].rate_vpm"}),
        ("avi_rate@1.2", {".stations[4].rate_vpm"}),
        ("buffer@0.8", {".buffer_vials"}),
        ("changeover@1.2", {".changeovers.scale"}),
        ("false_reject@0.8", {".quality.avi_false_reject_frac"}),
        ("defect_incidence@1.2", {".quality.defect_frac"}),
        ("qa_review@0.8", {".qa.review_mean_min"}),
        ("sublot_n@10", {".sublot_vials"}),
    ],
)
def test_each_perturbation_changes_only_its_parameter(cfgs, base, name, expected):
    assert set(_diff(base.model_dump(), cfgs[name]["config"].model_dump())) == expected


def test_failure_and_minor_stop_perturbations_touch_every_station_that_has_them(cfgs, base):
    for name, key, field in (
        ("mtbf@1.2", "failures", "mtbf_min"),
        ("mttr@0.8", "failures", "mttr_mean_min"),
        ("minor_stop_interval@0.8", "minor_stops", "mean_between_min"),
    ):
        changed = _diff(base.model_dump(), cfgs[name]["config"].model_dump())
        have = [i for i, s in enumerate(base.stations) if getattr(s, key)]
        assert sorted(changed) == sorted(f".stations[{i}].{key}.{field}" for i in have)
        lv = cfgs[name]["level"]
        for i in have:
            b, p = getattr(base.stations[i], key), getattr(cfgs[name]["config"].stations[i], key)
            assert getattr(p, field) == pytest.approx(getattr(b, field) * lv)


def test_batch_size_scales_every_batch(cfgs, base):
    c = cfgs["batch_size@1.2"]["config"]
    assert [b.size_vials for b in c.schedule] == [int(b.size_vials * 1.2) for b in base.schedule]

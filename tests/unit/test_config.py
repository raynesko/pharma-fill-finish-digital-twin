import copy
import sys
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from ffdt.config import LineConfig, apply_overrides, load_config

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "configs" / "baseline_line.yaml"


@pytest.fixture
def raw():
    return yaml.safe_load(BASE.read_text(encoding="utf-8"))


def test_baseline_loads_with_required_content():
    cfg = load_config(BASE)
    assert [s.name for s in cfg.stations] == [
        "washer",
        "tunnel",
        "filler",
        "capper",
        "avi",
        "labeler",
        "cartoner",
    ]  # + manual re-inspection pool = 8 stations
    assert cfg.staffing.inspector >= 1 and cfg.quality.manual_rate_vpm_per_inspector > 0
    assert len(cfg.products) >= 2 and len(cfg.formats) >= 2
    assert {(b.product, b.format) for b in cfg.schedule} >= {
        ("prod_a", "vial_2r"),
        ("prod_a", "vial_10r"),
        ("prod_b", "vial_10r"),
        ("prod_b", "vial_2r"),
    }
    assert cfg.total_vials == 600_000


def test_hash_is_stable_and_content_sensitive():
    a, b = load_config(BASE), load_config(BASE)
    assert a.hash() == b.hash()
    assert apply_overrides(a, {"changeovers": {"scale": 0.5}}).hash() != a.hash()


def test_overrides_merge_and_station_patch():
    cfg = load_config(BASE)
    new = apply_overrides(
        cfg, {"staffing": {"mechanic": 2}, "station_overrides": {"avi": {"count": 2}}}
    )
    assert new.staffing.mechanic == 2 and new.staffing.operator == cfg.staffing.operator
    assert new.station("avi").count == 2 and new.station("filler").count == 1
    with pytest.raises(ValueError, match="unknown stations"):
        apply_overrides(cfg, {"station_overrides": {"nope": {"count": 2}}})


def _mutate(raw, fn):
    d = copy.deepcopy(raw)
    fn(d)
    return d


NEGATIVE = {
    "zero rate": (lambda d: d["stations"][2].update(rate_vpm=0), "greater than 0"),
    "probability > 1": (
        lambda d: d["quality"].update(avi_detect_frac=1.2),
        "less than or equal to 1",
    ),
    "buffer < 10 sublots": (lambda d: d.update(buffer_vials=500), "at least 10 sub-lots"),
    "triangular order": (
        lambda d: d["changeovers"]["same_product"].update(mode_min=500),
        "low_min <= mode_min",
    ),
    "unknown product": (lambda d: d["schedule"][0].update(product="prod_z"), "unknown product"),
    "duplicate station": (
        lambda d: d["stations"].append(dict(d["stations"][0])),
        "duplicate station names",
    ),
    "typo field": (lambda d: d["staffing"].update(mechanics=2), "Extra inputs are not permitted"),
    "tunnel without residence": (
        lambda d: d["stations"][1].update(residence_min=0),
        "needs residence_min",
    ),
    "negative staff": (lambda d: d["staffing"].update(operator=-1), "greater than or equal to 0"),
}


@pytest.mark.parametrize("case", NEGATIVE, ids=list(NEGATIVE))
def test_invalid_configs_give_clear_errors(raw, case):
    fn, msg = NEGATIVE[case]
    with pytest.raises(ValidationError, match=msg):
        LineConfig.model_validate(_mutate(raw, fn))


def test_every_number_in_configs_cites_a_known_param_id():
    sys.path.insert(0, str(ROOT / "tools"))
    import check_param_ids

    assert check_param_ids.main([]) == 0


def test_param_checker_catches_orphans(tmp_path):
    sys.path.insert(0, str(ROOT / "tools"))
    import check_param_ids

    bad = tmp_path / "bad.yaml"
    bad.write_text("a: 5\nb: 6  # src: B-999\nc: 7  # src: B-001\n", encoding="utf-8")
    errs = check_param_ids.check(bad, check_param_ids.known_ids())
    assert len(errs) == 2


def test_param_checker_accepts_design_ticket_and_rejects_unknown(tmp_path):
    sys.path.insert(0, str(ROOT / "tools"))
    import check_param_ids

    f = tmp_path / "exp.yaml"
    f.write_text("n_reps: 30  # design: T4.1.3\nseed: 1  # design: T9.9.9\n", encoding="utf-8")
    errs = check_param_ids.check(f, check_param_ids.known_ids())
    assert len(errs) == 1 and "T9.9.9" in errs[0]

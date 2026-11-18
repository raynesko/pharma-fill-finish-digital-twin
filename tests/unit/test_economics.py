import json

import pytest

from ffdt.experiments import economics as E

D = json.loads(E.FINAL.read_text(encoding="utf-8"))


def test_doc_matches_generator():
    assert E.DOC.read_text(encoding="utf-8") == E.report(D)


def test_annual_vials_follow_from_results_and_calendar():
    assert E.ppt_hours_per_week() == 70  # 5 days x 2 shifts x (480 - 60) min
    scen = {s["scenario"]: s for s in D["scenarios"]}
    r = {x["scenario"]: x for x in E.rows(D)}["sc04_changeover_m50"]
    assert r["vials_yr"] == pytest.approx(
        scen["sc04_changeover_m50"]["good_per_ppt_hour_diff"] * 70 * 48
    )


def test_undetectable_gain_never_pays_back():
    r = {x["scenario"]: x for x in E.rows(D)}["sc01_avi_plus1"]
    assert not r["detectable"]
    assert all(v is None for v in r["payback_months"].values())
    assert r["worst_months"] is None


def test_every_price_is_labeled_placeholder_and_doc_says_illustrative():
    text = E.report(D)
    assert "Illustrative only. Not a business case." in text
    assert "not plant data" in text
    for line in text.splitlines():
        if "cost |" in line or "margin of one extra" in line:
            assert "PLACEHOLDER" in line and "range" in line

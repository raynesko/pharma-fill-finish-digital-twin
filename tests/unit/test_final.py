"""results_final.json is the single source of public numbers (T5.2.5)."""

import json
from pathlib import Path

import pytest

from ffdt.experiments import final

ROOT = Path(__file__).resolve().parents[2]
FINAL = ROOT / "reports" / "results_final.json"


@pytest.fixture(scope="module")
def d():
    return json.loads(FINAL.read_text(encoding="utf-8"))


def test_memo_is_rendered_from_the_frozen_json(d):
    """Every number in the memo comes from results_final.json: re-rendering reproduces it."""
    memo = (ROOT / "reports" / "scenario_findings.md").read_text(encoding="utf-8")
    assert final.memo(d) == memo


def test_frozen_and_labeled(d):
    assert d["frozen"] and d["number_type"] == "RESULT"
    assert "Simulated" in d["label"] and "Not plant data" in d["label"]


def test_scenario_rows_are_consistent(d):
    rows = d["scenarios"]
    assert len(rows) == 11 and sum(r["set"] == "main" for r in rows) == 10
    for r in rows:
        assert r["pct_ci_low"] <= r["pct_diff"] <= r["pct_ci_high"]
        assert (r["p_holm"] is None) == (r["set"] == "exploratory")
    assert [r["pct_diff"] for r in rows] == sorted((r["pct_diff"] for r in rows), reverse=True)


def test_every_preregistered_hypothesis_has_a_verdict(d):
    assert set(d["hypotheses"]) == {"H1a", "H1b", "H2a", "H2b", "H3a", "H3b", "H4a", "H4b", "H5"}


def test_portfolio_is_rendered_from_the_frozen_json(d):
    text = (ROOT / "docs" / "portfolio" / "resume_bullets.md").read_text(encoding="utf-8")
    assert final.portfolio(d) == text
    bullets = [ln for ln in text.splitlines() if ln[:2] in ("1.", "2.", "3.")]
    assert len(bullets) == 3 and all("simulated" in b.lower() for b in bullets)

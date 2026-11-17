import math
from pathlib import Path

import pytest

from ffdt.config import apply_overrides, load_config
from ffdt.sim.line import Line

BASE = Path(__file__).resolve().parents[2] / "configs" / "baseline_line.yaml"


@pytest.fixture(scope="module")
def cfg():
    return load_config(BASE)


def _run(cfg, seed=11, **quality):
    c = apply_overrides(cfg, {"quality": quality}) if quality else cfg
    line = Line(c, root_seed=seed, use_calendar=False, stochastic=False, changeovers=False)
    assert line.run()
    return line


def _within_binomial_95(k, n, p):
    sd = math.sqrt(n * p * (1 - p))
    return abs(k - n * p) <= 1.96 * sd + 1  # +1: discreteness


def test_zero_defects_zero_false_rejects_gives_full_quality(cfg):
    line = _run(cfg, defect_frac=0.0, avi_false_reject_frac=0.0, fill_weight_reject_frac=0.0)
    led = line.ledger
    assert led.scrapped == 0 and led.packed == cfg.total_vials
    assert line.quality.ledger.avi_true_rejects == line.quality.ledger.avi_false_rejects == 0


def test_yield_reconciles_with_conservation_and_causes(cfg):
    line = _run(cfg)
    led, q = line.ledger, line.quality.ledger
    assert led.started == led.packed + led.scrapped
    assert led.scrapped == sum(q.scrapped.values())
    assert sum(b.scrapped for b in led.batches) == led.scrapped
    # every AVI reject is either scrapped (confirmed) or returned to the flow
    assert (
        q.avi_true_rejects + q.avi_false_rejects
        == q.scrapped["avi_confirmed"] + q.reworked_returned
    )
    yield_ = led.packed / led.started
    assert 0.98 < yield_ < 1.0


def test_sampled_fractions_within_binomial_bounds(cfg):
    line = _run(cfg, seed=12)
    qc, q = cfg.quality, line.quality.ledger
    n = cfg.total_vials
    assert _within_binomial_95(q.scrapped["fill_weight"], n, qc.fill_weight_reject_frac)
    filled = n - q.scrapped["fill_weight"]
    assert _within_binomial_95(q.defects_created, filled, qc.defect_frac)
    assert _within_binomial_95(q.avi_true_rejects, q.defects_created, qc.avi_detect_frac)
    good = filled - q.defects_created
    assert _within_binomial_95(q.avi_false_rejects, good, qc.avi_false_reject_frac)
    assert _within_binomial_95(
        q.scrapped["avi_confirmed"], q.avi_true_rejects, qc.manual_confirm_frac
    )


def test_escapes_are_defects_not_removed(cfg):
    line = _run(cfg, seed=13)
    q = line.quality.ledger
    assert q.escapes == q.defects_created - q.scrapped["avi_confirmed"]


def test_manual_inspection_pool_runs_and_returns_rework(cfg):
    line = _run(cfg)
    units = {u for st, u, *_ in line.log.states if st == "manual_inspection"}
    assert units == set(range(cfg.staffing.inspector))
    assert line.quality.ledger.reworked_returned > 0


def test_same_seed_same_quality_outcome(cfg):
    a, b = _run(cfg, seed=21), _run(cfg, seed=21)
    assert a.quality.ledger == b.quality.ledger

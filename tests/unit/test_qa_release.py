from pathlib import Path

import numpy as np
import pytest

from ffdt.config import apply_overrides, load_config
from ffdt.sim.line import Line

BASE = Path(__file__).resolve().parents[2] / "configs" / "baseline_line.yaml"


@pytest.fixture(scope="module")
def cfg():
    return load_config(BASE)


def test_every_batch_gets_lead_time_and_queue_time(cfg):
    line = Line(cfg, root_seed=7)
    assert line.run()
    for b in line.ledger.batches:
        assert b.release_min >= b.end_min + cfg.qa.review_min_min
        assert b.qa_queue_min >= 0
        assert b.lead_time_min == pytest.approx(b.release_min - b.start_min)
    assert line.env.now > line.campaign_end_min  # QA ran on after the line stopped


def test_qa_hold_does_not_change_equipment_states(cfg):
    """D5 under common random numbers: toggling QA or its hold leaves the state log identical."""
    long_hold = apply_overrides(cfg, {"qa": {"release_hold_min": 20160, "reviewers": 1}})
    runs = [Line(cfg, root_seed=9), Line(long_hold, root_seed=9), Line(cfg, root_seed=9, qa=False)]
    for line in runs:
        assert line.run()
    assert runs[0].log.states == runs[1].log.states == runs[2].log.states
    assert runs[0].campaign_end_min == runs[2].campaign_end_min


def test_release_hold_adds_exactly(cfg):
    hold = apply_overrides(cfg, {"qa": {"release_hold_min": 1000}})
    a, b = Line(cfg, root_seed=3), Line(hold, root_seed=3)
    a.run(), b.run()
    for x, y in zip(a.ledger.batches, b.ledger.batches, strict=True):
        assert y.release_min - x.release_min == pytest.approx(1000)


def test_one_reviewer_queues_more(cfg):
    one = apply_overrides(cfg, {"qa": {"reviewers": 1}})
    a, b = Line(cfg, root_seed=5), Line(one, root_seed=5)
    a.run(), b.run()
    qa = sum(r.qa_queue_min for r in a.ledger.batches)
    qb = sum(r.qa_queue_min for r in b.ledger.batches)
    assert qb >= qa and qb > 0


def test_review_time_distribution_matches_config(cfg):
    line = Line(cfg, qa=True)
    d = line.qa.dist
    x = d.sample(np.random.default_rng(0), 100_000)
    assert x.min() >= cfg.qa.review_min_min
    assert x.mean() == pytest.approx(cfg.qa.review_mean_min, rel=0.02)

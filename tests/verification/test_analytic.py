"""Simulator vs closed forms (T4.1.2). Slow checks run with ``python tasks.py verify``."""

from pathlib import Path

import pytest

from ffdt.config import load_config
from ffdt.experiments import analytic as A
from ffdt.metrics import ledger as L
from ffdt.sim.line import Line

BASE = Path(__file__).resolve().parents[2] / "configs" / "baseline_line.yaml"


@pytest.mark.slow
def test_mm1_queue_wait_within_2pct_and_ci():
    c = A.mm1_wait()
    assert c.n_reps >= 30
    assert abs(c.rel_error) < 0.02
    assert c.theory_in_ci


@pytest.mark.slow
def test_mm1k_blocking_probability_in_ci():
    c = A.mm1k_block()
    assert c.n_reps >= 30
    assert c.theory_in_ci


def test_availability_formula_in_ci():
    c = A.availability()
    assert c.theory_in_ci and abs(c.rel_error) < 0.005


def test_service_moments_are_near_exponential():
    es, es2 = A.service_moments(1000)
    assert es == pytest.approx(1.0)
    assert es2 == pytest.approx(2 * es**2, rel=0.001)  # exponential: E[S^2] = 2 E[S]^2


@pytest.mark.parametrize("rep", [0, 1, 2])
def test_littles_law_under_1pct_on_every_buffer(rep):
    line = Line(load_config(BASE), root_seed=20261116, replication=rep)
    assert line.run()
    q = L.queue_stats(line.export())
    assert len(q) == 8
    assert (abs(q["littles_ratio"] - 1) < 0.01).all()

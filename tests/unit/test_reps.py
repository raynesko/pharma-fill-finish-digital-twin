import numpy as np
import pytest
from scipy import stats

from ffdt.experiments import reps


def test_required_reps_matches_closed_form_check():
    rng = np.random.default_rng(0)
    x = rng.normal(100, 4, size=20)  # cv ~ 4%
    n = reps.required_reps(x, rel=0.02)
    mean, s = x.mean(), x.std(ddof=1)
    hw = lambda k: stats.t.ppf(0.975, k - 1) * s / np.sqrt(k)  # noqa: E731
    assert hw(n) <= 0.02 * mean < hw(n - 1)


def test_zero_variance_needs_two_reps():
    assert reps.required_reps(np.full(10, 5.0)) == 2


def test_welch_flat_series_and_warmup_detection():
    ramp = np.r_[np.linspace(0, 100, 5), np.full(95, 100.0)]
    series = np.tile(ramp, (4, 1))
    ma = reps.welch(series, window=3)
    assert len(ma) == 97
    assert ma[-1] == pytest.approx(100)
    w = reps.warmup_end(ma, tol=0.02)
    assert w == 7  # window 3 reaches the plateau once it no longer sees the ramp (y[4:11])
    noisy = ma.copy()
    noisy[50] *= 1.2  # a late excursion must not push the warm-up end out
    assert reps.warmup_end(noisy, tol=0.02) == w


def test_half_width_t_based():
    x = np.array([1.0, 2.0, 3.0])
    assert reps.half_width(x) == pytest.approx(stats.t.ppf(0.975, 2) * 1 / np.sqrt(3))

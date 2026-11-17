import ast
import math
from pathlib import Path

import numpy as np
import pytest

from ffdt import params as P
from ffdt.rng import stream

N = 100_000

CASES = [
    P.exponential_from_mean(4800),
    P.lognormal_from_mean_cv(75, 0.8),
    P.lognormal_from_mean_cv(75, 0.5),
    P.triangular(390, 600, 900),
    P.triangular(45, 90, 150),
    P.shifted_lognormal(480, 2880, 0.8),
    P.weibull_from_mean(4800, 2.0),
    P.weibull_from_mean(4800, 1.0),
]


@pytest.mark.parametrize("d", CASES, ids=lambda d: f"{d.kind}{d.params}")
def test_sample_mean_and_cv_match_targets(d):
    x = d.sample(stream(1, 0, f"test.{d.kind}"), N)
    assert x.min() >= 0
    assert abs(x.mean() / d.mean - 1) < 0.01  # within 1% (target)
    assert abs((x.std() / x.mean()) / d.cv - 1) < 0.03  # within 3% (target)


def test_weibull_shape_one_is_exponential():
    assert math.isclose(P.weibull_from_mean(100, 1.0).cv, 1.0)


@pytest.mark.parametrize("d", CASES, ids=lambda d: d.kind)
def test_scaled_scales_mean_keeps_cv(d):
    s = P.scaled(d, 0.5)
    assert math.isclose(s.mean, d.mean * 0.5)
    x = s.sample(stream(2, 0, "scaled"), N)
    assert abs(x.mean() / s.mean - 1) < 0.01


def test_constant():
    d = P.constant(30)
    assert d.sample(stream(0, 0, "c")) == 30
    assert (d.sample(stream(0, 0, "c"), 3) == 30).all()


@pytest.mark.parametrize(
    "bad",
    [
        lambda: P.exponential_from_mean(0),
        lambda: P.lognormal_from_mean_cv(10, -1),
        lambda: P.triangular(5, 1, 10),
        lambda: P.triangular(5, 5, 5),
        lambda: P.shifted_lognormal(100, 50, 0.5),
        lambda: P.constant(-1),
        lambda: P.weibull_from_mean(10, 0),
    ],
)
def test_invalid_parameters_raise(bad):
    with pytest.raises(ValueError):
        bad()


def test_streams_are_reproducible_and_name_keyed():
    a1 = stream(42, 3, "filler.failures").random(5)
    a2 = stream(42, 3, "filler.failures").random(5)
    b = stream(42, 3, "avi.failures").random(5)
    c = stream(42, 4, "filler.failures").random(5)
    assert np.array_equal(a1, a2)
    assert not np.array_equal(a1, b)
    assert not np.array_equal(a1, c)


def test_no_global_rng_in_package():
    """No np.random.<fn>(...) calls on the global RNG anywhere in src/ffdt."""
    allowed = {"Generator", "PCG64", "SeedSequence", "default_rng"}
    src = Path(__file__).resolve().parents[2] / "src" / "ffdt"
    for f in src.rglob("*.py"):
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Attribute)
                and node.value.attr == "random"
            ):
                assert node.attr in allowed, f"{f.name}: np.random.{node.attr}"

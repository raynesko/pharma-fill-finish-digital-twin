"""Sampling distributions built from benchmark summaries (T2.1.3).

All times are in **minutes**. Every distribution samples only from a ``numpy.random.Generator``
passed in by the caller (never the global RNG); generators come from :func:`ffdt.rng.stream`.

Distribution choices are justified in ``docs/assumptions.md`` (A-035..A-042):

* time to failure: exponential from MTBF (Weibull available when wear-out data exist)
* repair time: lognormal from mean and coefficient of variation (CV)
* changeover: triangular from low / mode / high
* QA review: shifted lognormal (minimum effort + right-skewed delay)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Distribution:
    """A sampling distribution with analytic mean and CV (for tests and documentation)."""

    kind: str
    params: tuple[float, ...]
    mean: float
    cv: float

    def sample(self, rng: np.random.Generator, size: int | None = None):
        p = self.params
        if self.kind == "constant":
            return p[0] if size is None else np.full(size, p[0])
        if self.kind == "exponential":
            return rng.exponential(p[0], size)
        if self.kind == "lognormal":
            return rng.lognormal(p[0], p[1], size)
        if self.kind == "shifted_lognormal":
            return p[0] + rng.lognormal(p[1], p[2], size)
        if self.kind == "triangular":
            return rng.triangular(p[0], p[1], p[2], size)
        if self.kind == "weibull":
            return p[1] * rng.weibull(p[0], size)
        raise ValueError(f"unknown distribution kind {self.kind!r}")


def _positive(name: str, value: float) -> None:
    if not value > 0:
        raise ValueError(f"{name} must be > 0 (got {value})")


def constant(value_min: float) -> Distribution:
    """Deterministic duration in minutes (used for verification and fixed holds)."""
    if value_min < 0:
        raise ValueError(f"value_min must be >= 0 (got {value_min})")
    return Distribution("constant", (value_min,), value_min, 0.0)


def exponential_from_mean(mean_min: float) -> Distribution:
    """Exponential with the given mean in minutes (e.g., time to failure from MTBF)."""
    _positive("mean_min", mean_min)
    return Distribution("exponential", (mean_min,), mean_min, 1.0)


def lognormal_from_mean_cv(mean_min: float, cv: float) -> Distribution:
    """Lognormal parameterized by its own mean (minutes) and CV.

    sigma^2 = ln(1 + cv^2); mu = ln(mean) - sigma^2 / 2.
    """
    _positive("mean_min", mean_min)
    _positive("cv", cv)
    s2 = math.log1p(cv * cv)
    mu = math.log(mean_min) - s2 / 2
    return Distribution("lognormal", (mu, math.sqrt(s2)), mean_min, cv)


def shifted_lognormal(min_min: float, mean_min: float, cv_excess: float) -> Distribution:
    """``min_min`` + lognormal excess. ``mean_min`` is the TOTAL mean; ``cv_excess`` is the CV
    of the part above the minimum."""
    if min_min < 0:
        raise ValueError(f"min_min must be >= 0 (got {min_min})")
    if not mean_min > min_min:
        raise ValueError("mean_min must exceed min_min")
    excess = lognormal_from_mean_cv(mean_min - min_min, cv_excess)
    sd = (mean_min - min_min) * cv_excess
    return Distribution("shifted_lognormal", (min_min, *excess.params), mean_min, sd / mean_min)


def triangular(low_min: float, mode_min: float, high_min: float) -> Distribution:
    """Triangular from low / mode / high (minutes); for 'no data' estimates such as changeovers."""
    if not (0 <= low_min <= mode_min <= high_min) or low_min == high_min:
        raise ValueError("need 0 <= low <= mode <= high and low < high")
    a, c, b = low_min, mode_min, high_min
    mean = (a + b + c) / 3
    var = (a * a + b * b + c * c - a * b - a * c - b * c) / 18
    return Distribution("triangular", (a, c, b), mean, math.sqrt(var) / mean)


def weibull_from_mean(mean_min: float, shape: float) -> Distribution:
    """Weibull with given mean (minutes) and shape k; scale = mean / Gamma(1 + 1/k).

    k = 1 is exponential; k > 1 models wear-out. Not used in baseline v1.0 (no wear data).
    """
    _positive("mean_min", mean_min)
    _positive("shape", shape)
    g1 = math.gamma(1 + 1 / shape)
    g2 = math.gamma(1 + 2 / shape)
    scale = mean_min / g1
    return Distribution("weibull", (shape, scale), mean_min, math.sqrt(g2 / (g1 * g1) - 1))


def scaled(dist: Distribution, factor: float) -> Distribution:
    """Same shape, every duration multiplied by ``factor`` (used by scenarios and sensitivity,
    e.g. changeover -50% is ``scaled(d, 0.5)``). CV is unchanged."""
    _positive("factor", factor)
    p = dist.params
    if dist.kind in ("constant", "exponential"):
        new = (p[0] * factor,)
    elif dist.kind == "triangular":
        new = tuple(x * factor for x in p)
    elif dist.kind == "lognormal":
        new = (p[0] + math.log(factor), p[1])
    elif dist.kind == "shifted_lognormal":
        new = (p[0] * factor, p[1] + math.log(factor), p[2])
    elif dist.kind == "weibull":
        new = (p[0], p[1] * factor)
    else:
        raise ValueError(dist.kind)
    return Distribution(dist.kind, new, dist.mean * factor, dist.cv)

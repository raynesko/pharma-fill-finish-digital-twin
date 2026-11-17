"""Run length, warm-up and replication count (T4.1.3).

Primary mode is TERMINATING: one campaign from an empty, clean line until every batch is packed.
That matches the real system (a campaign starts after a full clean and line clearance), so no
warm-up is deleted. Steady-state mode exists only as a verification aid: one very large batch on
an always-on calendar, analysed with Welch's moving-average method.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats

from ffdt.config import LineConfig, apply_overrides
from ffdt.sim.line import Line


def steady_state_config(cfg: LineConfig, vials: int = 5_000_000) -> LineConfig:
    """One huge batch: no changeovers inside the horizon; failures and quality stay on."""
    b = cfg.schedule[0]
    return apply_overrides(
        cfg, {"schedule": [{"product": b.product, "format": b.format, "size_vials": vials}]}
    )


def hourly_output(cfg: LineConfig, seed: int, rep: int, hours: int) -> np.ndarray:
    """Good vials packed in each hour of a steady-state run (always-on calendar)."""
    line = Line(cfg, root_seed=seed, replication=rep, use_calendar=False)
    line.run(max_min=hours * 60)
    t = np.array([f[0] for f in line.log.flow if f[1] == "packed"])
    v = np.array([f[3] for f in line.log.flow if f[1] == "packed"])
    out = np.zeros(hours)
    np.add.at(out, np.minimum((t // 60).astype(int), hours - 1), v)
    return out


def welch(series: np.ndarray, window: int) -> np.ndarray:
    """Welch moving average of the across-replication mean (rows = replications).
    Early points use the shrinking symmetric window from Law (2015) section 9.5.1."""
    y = series.mean(axis=0)
    m = len(y)
    out = np.empty(m - window)
    for i in range(m - window):
        w = min(i, window)
        out[i] = y[i - w : i + w + 1].mean()
    return out


def warmup_end(ma: np.ndarray, tol: float = 0.05) -> int:
    """First index at which the moving average reaches within ``tol`` of its mean over the
    second half of the run. A simple documented rule, to be confirmed by eye on the Welch plot:
    with random breakdowns the average keeps wandering a few percent, so a "stays inside the
    band" rule never triggers."""
    ref = ma[len(ma) // 2 :].mean()
    hits = np.flatnonzero(np.abs(ma / ref - 1) <= tol)
    return int(hits[0]) if len(hits) else len(ma)


def half_width(x, level: float = 0.95) -> float:
    x = np.asarray(x, dtype=float)
    return float(stats.t.ppf((1 + level) / 2, len(x) - 1) * x.std(ddof=1) / math.sqrt(len(x)))


def required_reps(x, rel: float = 0.02, level: float = 0.95, n_max: int = 1000) -> int:
    """Smallest n with t_{n-1} s / sqrt(n) <= rel x mean, using the pilot's mean and s
    (Law 2015, sequential approximation)."""
    x = np.asarray(x, dtype=float)
    mean, s = abs(x.mean()), x.std(ddof=1)
    for n in range(2, n_max + 1):
        if stats.t.ppf((1 + level) / 2, n - 1) * s / math.sqrt(n) <= rel * mean:
            return n
    return n_max


def pilot_table(summary: pd.DataFrame, metrics: list[str], rel: float = 0.02) -> pd.DataFrame:
    rows = []
    for m in metrics:
        x = summary[m].to_numpy(dtype=float)
        rows.append(
            {
                "metric": m,
                "pilot_n": len(x),
                "mean": x.mean(),
                "sd": x.std(ddof=1),
                "cv": x.std(ddof=1) / x.mean(),
                "half_width_pilot": half_width(x),
                "rel_half_width_pilot": half_width(x) / x.mean(),
                "n_required": required_reps(x, rel),
            }
        )
    return pd.DataFrame(rows)

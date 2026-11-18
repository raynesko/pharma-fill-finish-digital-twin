"""Paired scenario-vs-baseline comparison (T5.2.1; rules in docs/scenario_matrix.md).

Replication r of a scenario is paired with replication r of the baseline (common random
numbers), so the comparison uses the per-replication differences d_r = scenario_r - baseline_r:
mean, t-based 95% CI, paired t-test p-value, a percentile bootstrap CI as a cross-check, and the
unpaired (Welch) CI width to show what common random numbers bought. Holm adjusts the p-values of
the pre-registered main set on the primary metric; exploratory comparisons are never adjusted.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

PRIMARY = "good_per_ppt_hour"
# practical significance (TARGET, docs/scenario_matrix.md): +3% good vials/h or +2 OEE points
PRACTICAL = {"good_per_ppt_hour": ("rel", 0.03), "line_oee": ("abs", 0.02)}
METRICS = [
    "good_per_ppt_hour",
    "line_oee",
    "line_A",
    "changeover_share",
    "wait_staff_share",
    "mean_lead_time_h",
    "makespan_h",
]
# Bootstrap cross-check tolerance (stated, not tuned): each bootstrap CI end must lie within
# BOOT_TOL x the paired t half-width of the matching t-CI end. Where it does not, the paired
# differences are usually degenerate (mostly exactly 0 with a few outliers), the t-interval's
# normality assumption fails, and both intervals are reported.
BOOT_TOL = 0.15


@dataclass
class Paired:
    n: int
    base_mean: float
    mean_diff: float
    ci_low: float
    ci_high: float
    p: float
    boot_low: float
    boot_high: float
    unpaired_half_width: float
    zero_frac: float  # share of replications whose paired difference is exactly 0

    @property
    def half_width(self) -> float:
        return (self.ci_high - self.ci_low) / 2

    @property
    def boot_agrees(self) -> bool:
        gap = max(abs(self.ci_low - self.boot_low), abs(self.ci_high - self.boot_high))
        return gap <= BOOT_TOL * self.half_width + 1e-12


def paired(base, scen, level: float = 0.95, n_boot: int = 10_000, seed: int = 0) -> Paired:
    base, scen = np.asarray(base, float), np.asarray(scen, float)
    if base.shape != scen.shape or len(base) < 2:
        raise ValueError("need equal-length samples with n >= 2")
    d = scen - base
    n, m, s = len(d), float(d.mean()), float(d.std(ddof=1))
    tq = stats.t.ppf((1 + level) / 2, n - 1)
    hw = tq * s / math.sqrt(n)
    if s == 0:
        p = 0.0 if m != 0 else 1.0
    else:
        p = float(stats.ttest_rel(scen, base).pvalue)
    rng = np.random.default_rng(seed)
    boots = d[rng.integers(0, n, size=(n_boot, n))].mean(axis=1)
    lo, hi = np.quantile(boots, [(1 - level) / 2, (1 + level) / 2])
    v = scen.var(ddof=1) / n + base.var(ddof=1) / n
    dof = (
        v**2 / ((scen.var(ddof=1) / n) ** 2 / (n - 1) + (base.var(ddof=1) / n) ** 2 / (n - 1))
        if v > 0
        else n - 1
    )
    unpaired_hw = float(stats.t.ppf((1 + level) / 2, dof) * math.sqrt(v))
    zero = float(np.mean(d == 0))
    return Paired(
        n, float(base.mean()), m, m - hw, m + hw, p, float(lo), float(hi), unpaired_hw, zero
    )


def holm(pvals) -> np.ndarray:
    """Holm step-down adjusted p-values (monotone, capped at 1)."""
    p = np.asarray(pvals, float)
    order = np.argsort(p)
    k = len(p)
    adj = np.empty(k)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (k - rank) * p[i])
        adj[i] = min(1.0, running)
    return adj


def practical_flag(metric: str, base_mean: float, mean_diff: float) -> bool | None:
    if metric not in PRACTICAL:
        return None
    kind, thr = PRACTICAL[metric]
    effect = mean_diff / base_mean if kind == "rel" else mean_diff
    return abs(effect) >= thr


def load_results(results_dir: Path) -> dict[str, pd.DataFrame]:
    """{scenario: summary with changeover_share and wait_staff_share added}, by replication."""
    out = {}
    for d in sorted(p for p in results_dir.iterdir() if p.is_dir() and not p.name.startswith("_")):
        summ = pd.read_parquet(d / f"{d.name}.summary.parquet")
        par = pd.read_parquet(d / f"{d.name}.pareto.parquet")
        shares = par.pivot_table(index="replication", columns="category", values="share_of_ppt")
        summ = summ.set_index("replication")
        summ["changeover_share"] = shares["CHANGEOVER"]
        summ["wait_staff_share"] = shares["WAIT_STAFF"]
        out[d.name] = summ.sort_index()
    return out


def compare(results: dict[str, pd.DataFrame], meta: pd.DataFrame) -> pd.DataFrame:
    """One row per scenario x metric. ``meta`` has columns name, family, exploratory."""
    base = results["baseline"]
    rows = []
    for sc in meta.itertuples():
        if sc.name not in results:
            continue
        s = results[sc.name]
        assert (s.index == base.index).all(), "replications must pair one-to-one"
        for metric in METRICS:
            r = paired(base[metric], s[metric])
            rows.append(
                {
                    "scenario": sc.name,
                    "family": sc.family,
                    "set": "exploratory" if sc.exploratory else "main",
                    "metric": metric,
                    "primary": metric == PRIMARY,
                    "base_mean": r.base_mean,
                    "mean_diff": r.mean_diff,
                    "pct_diff": r.mean_diff / r.base_mean if r.base_mean else np.nan,
                    "ci_low": r.ci_low,
                    "ci_high": r.ci_high,
                    "p": r.p,
                    "boot_low": r.boot_low,
                    "boot_high": r.boot_high,
                    "paired_half_width": r.half_width,
                    "unpaired_half_width": r.unpaired_half_width,
                    "boot_agrees": r.boot_agrees,
                    "zero_diff_frac": r.zero_frac,
                    "practical": practical_flag(metric, r.base_mean, r.mean_diff),
                    "n": r.n,
                }
            )
    df = pd.DataFrame(rows)
    df["p_holm"] = np.nan
    mask = df["primary"] & (df["set"] == "main")
    df.loc[mask, "p_holm"] = holm(df.loc[mask, "p"])
    return df


def run(results_dir: Path | None = None) -> pd.DataFrame:
    """Compare every scenario in ``results_dir`` with the baseline; write comparison.{csv,parquet}."""
    from ffdt.experiments import scenarios as sc

    results_dir = results_dir or sc.RESULTS
    meta = pd.DataFrame(
        [
            {"name": s.name, "family": s.family, "exploratory": s.exploratory}
            for s in sc.all_scenarios()
        ]
    )
    df = compare(load_results(results_dir), meta)
    df.to_parquet(results_dir / "comparison.parquet", index=False)
    df.to_csv(results_dir / "comparison.csv", index=False)
    return df


if __name__ == "__main__":
    out = run()
    prim = out[out["primary"]]
    print(prim[["scenario", "set", "pct_diff", "ci_low", "ci_high", "p_holm", "practical"]])

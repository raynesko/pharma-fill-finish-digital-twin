"""Baseline results report (T4.2.3): numbers for reports/baseline.md and results_baseline.json.

Reads only the baseline parquet files written by ``python tasks.py scenarios``
(results/baseline/). Every interval is a t-based 95% CI over the 30 replications chosen in
T4.1.3. The bottleneck section reports evidence only (utilization, starvation, blocking and
queue in front of each station); the constraint is identified in T5.2.3 with several methods.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ffdt.experiments.analytic import t_ci

SIM_LABEL = "Simulated, benchmark-parameterized. Not plant data."
STATES = ["RUN", "STARVED", "BLOCKED", "DOWN", "MINOR_STOP", "CHANGEOVER", "WAIT_STAFF"]
LINE_METRICS = [
    "line_oee",
    "line_A",
    "line_P",
    "line_Q",
    "good_per_ppt_hour",
    "good_per_calendar_hour",
    "makespan_h",
    "yield",
    "mean_cycle_time_h",
    "mean_lead_time_h",
    "mean_qa_queue_h",
    "wip_mean_vials",
]


def _ci(x) -> dict:
    m, lo, hi = t_ci(x)
    return {"mean": m, "ci_low": lo, "ci_high": hi}


def load(results_dir: Path, name: str = "baseline") -> dict[str, pd.DataFrame]:
    d = results_dir / name
    return {
        k: pd.read_parquet(d / f"{name}.{k}.parquet")
        for k in ("summary", "stations", "pareto", "queues")
    }


def line_table(summary: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({m: _ci(summary[m]) for m in LINE_METRICS}).T


def station_oee_table(stations: pd.DataFrame) -> pd.DataFrame:
    """Mean and 95% CI of A, P, Q, OEE per station, in line order."""
    rows = []
    for st, g in stations.groupby("station", sort=False):
        row = {"station": st}
        for m in ("A", "P", "Q", "OEE"):
            c = _ci(g[m])
            row |= {m: c["mean"], f"{m}_ci_low": c["ci_low"], f"{m}_ci_high": c["ci_high"]}
        rows.append(row)
    return pd.DataFrame(rows).set_index("station")


def state_shares(stations: pd.DataFrame) -> pd.DataFrame:
    """Share of scheduled production time (PPT) in each state, per station (mean over reps).
    Planned stops are outside PPT, so each row sums to 1."""
    s = stations.copy()
    for st in STATES:
        s[st] = s[f"{st}_min"] / s["ppt_min"]
    return s.groupby("station", sort=False)[STATES].mean()


def pareto_table(pareto: pd.DataFrame) -> pd.DataFrame:
    g = pareto.groupby(["category", "six_big_loss", "factor"], sort=False)["share_of_ppt"]
    out = g.apply(lambda x: pd.Series(_ci(x))).unstack().reset_index()
    return out[out["mean"] > 1e-9].sort_values("mean", ascending=False).reset_index(drop=True)


def bottleneck_evidence(stations: pd.DataFrame, queues: pd.DataFrame) -> pd.DataFrame:
    """Per line station: utilization, starved and blocked share of PPT, mean queue in front.
    Evidence only; no station is named the constraint here (T5.2.3 does that)."""
    sh = state_shares(stations)
    util = stations.groupby("station", sort=False)["utilization"].mean()
    rate = stations.groupby("station", sort=False)["rate_vpm"].first()
    q = queues.groupby("buffer")["mean_sublots"].mean()
    out = pd.DataFrame(
        {
            "rate_vpm": rate,
            "utilization": util,
            "starved_share": sh["STARVED"],
            "blocked_share": sh["BLOCKED"],
            "mean_queue_in_front_sublots": [q.get(f"in:{s}", float("nan")) for s in util.index],
        }
    )
    return out.drop(index=["manual_inspection"], errors="ignore")


def _records(df: pd.DataFrame) -> dict:
    return json.loads(df.to_json(orient="index", double_precision=6))


def build(results_dir: Path) -> dict:
    t = load(results_dir)
    summ = t["summary"]
    return {
        "label": SIM_LABEL,
        "number_type": "RESULT",
        "config_hash": str(summ["config_hash"].iloc[0]),
        "root_seed": int(summ["root_seed"].iloc[0]),
        "n_reps": int(len(summ)),
        "all_completed": bool(summ["completed"].all()),
        "ci": "t-based 95% over replications (T4.1.3)",
        "line": _records(line_table(summ)),
        "stations_oee": _records(station_oee_table(t["stations"])),
        "state_shares_of_ppt": _records(state_shares(t["stations"])),
        "loss_pareto": json.loads(
            pareto_table(t["pareto"]).to_json(orient="records", double_precision=6)
        ),
        "bottleneck_evidence": _records(bottleneck_evidence(t["stations"], t["queues"])),
    }


def write(results_dir: Path, out: Path) -> dict:
    data = build(results_dir)
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data


def _pct(c: dict, nd: int = 1) -> str:
    lo, hi = 100 * c["ci_low"], 100 * c["ci_high"]
    return f"{100 * c['mean']:.{nd}f}% (95% CI {lo:.{nd}f} to {hi:.{nd}f})"


def _num(c: dict, nd: int = 0) -> str:
    return f"{c['mean']:,.{nd}f} (95% CI {c['ci_low']:,.{nd}f} to {c['ci_high']:,.{nd}f})"


def markdown(d: dict) -> str:
    """reports/baseline.md, generated from results_baseline.json so no number is hand-copied."""
    ln = d["line"]
    done = "yes" if d["all_completed"] else "NO"
    out = [
        "# Baseline results (v1.0)",
        "",
        f"**{d['label']}** Every number below is a RESULT from `reports/results_baseline.json` "
        f"(generated by `notebooks/05_baseline_report.ipynb`): config hash `{d['config_hash']}`, "
        f"seed {d['root_seed']}, {d['n_reps']} replications, all completed: {done}. "
        f"Intervals: {d['ci']}.",
        "",
        "## Line",
        "| Metric | Result |",
        "|---|---|",
        f"| Line OEE (filler-referenced, D4) | {_pct(ln['line_oee'])} |",
        f"| Availability / Performance / Quality | {100 * ln['line_A']['mean']:.1f}% / "
        f"{100 * ln['line_P']['mean']:.1f}% / {100 * ln['line_Q']['mean']:.2f}% |",
        f"| Good vials per scheduled-production hour (primary) | {_num(ln['good_per_ppt_hour'])} |",
        f"| Good vials per calendar hour | {_num(ln['good_per_calendar_hour'])} |",
        f"| Campaign makespan, h | {_num(ln['makespan_h'], 1)} |",
        f"| Mean batch cycle time (start to last vial packed), h | "
        f"{_num(ln['mean_cycle_time_h'], 1)} |",
        f"| Mean batch lead time incl. QA release, h | {_num(ln['mean_lead_time_h'], 1)} |",
        f"| Mean WIP, vials | {_num(ln['wip_mean_vials'])} |",
        "",
        "## Station OEE",
        "| Station | A | P | Q | OEE (95% CI) |",
        "|---|---|---|---|---|",
    ]
    for st, r in d["stations_oee"].items():
        if st == "manual_inspection":
            continue
        out.append(
            f"| {st} | {100 * r['A']:.1f}% | {100 * r['P']:.1f}% | {100 * r['Q']:.2f}% | "
            f"{100 * r['OEE']:.1f}% ({100 * r['OEE_ci_low']:.1f} to {100 * r['OEE_ci_high']:.1f}) |"
        )
    out += [
        "",
        "Station P includes starvation and blocking (D3), so a fast station that waits on a slower "
        "one shows low P without being at fault. Station Q is below 100% only where vials leave "
        "the flow: fill-weight rejects at the filler and AVI rejects (sent to manual "
        "re-inspection, where most return to the flow). The offline manual-inspection pool is left "
        "out (its OEE is not meaningful; see `docs/metrics_schema.md`).",
        "",
        "## Loss Pareto at the filler (share of scheduled production time)",
        "| Loss | Six big losses | Factor | Share (95% CI) |",
        "|---|---|---|---|",
    ]
    for r in d["loss_pareto"]:
        if r["mean"] >= 1e-6:
            out.append(f"| {r['category']} | {r['six_big_loss']} | {r['factor']} | {_pct(r, 2)} |")
    out += [
        "",
        "Waiting for staff is zero in most replications, so its t-interval can dip below 0; read "
        'it as "under 1% of scheduled time".',
        "",
        "## Preliminary bottleneck evidence",
        "Evidence only; the constraint is identified in T5.2.3 with several methods.",
        "",
        "| Station | Rate, vials/min | Utilization | Starved | Blocked | Queue in front, sub-lots |",
        "|---|---|---|---|---|---|",
    ]
    for st, r in d["bottleneck_evidence"].items():
        out.append(
            f"| {st} | {r['rate_vpm']:.0f} | {100 * r['utilization']:.1f}% | "
            f"{100 * r['starved_share']:.1f}% | {100 * r['blocked_share']:.1f}% | "
            f"{r['mean_queue_in_front_sublots']:.1f} |"
        )
    out += [
        "",
        "Reading notes: starved and blocked are shares of scheduled production time. Buffers hold "
        "at most 20 sub-lots. The queue in front of the washer is vials waiting to be released "
        "into the line and sits near its cap by construction, so it is not constraint evidence.",
        "",
        "Figures (simulated, benchmark-parameterized): `reports/figures/05_station_oee.png`, "
        "`reports/figures/05_loss_pareto.png`, `reports/figures/05_station_states.png`.",
        "",
    ]
    return "\n".join(out)


if __name__ == "__main__":
    # same outputs as notebooks/05_baseline_report.ipynb, without the figures
    root = Path(__file__).resolve().parents[3]
    d = write(root / "results", root / "reports" / "results_baseline.json")
    (root / "reports" / "baseline.md").write_text(markdown(d), encoding="utf-8")

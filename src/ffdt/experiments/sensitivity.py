"""One-at-a-time sensitivity analysis (T5.2.2).

Every Sens = Y assumption in docs/assumptions.md is perturbed by -20% and +20% (sub-lot size N
uses the levels 10 and 200 instead, to expose discretization error; 500, as planned, is
infeasible: ADR-001 needs the 2,000-vial buffers to hold 10 sub-lots), one at a time, around the
frozen baseline v1.0. Each perturbed configuration runs the project's experiment design (30
replications, seed 20261116) and is compared with the baseline replication by replication
(common random numbers), so each bar of the tornado is a paired difference with a 95% CI.

Two checks on the study's conclusions:
- **Bottleneck flip:** the constraint of every perturbed configuration by the three run-level
  methods (utilization, blocking/starvation arrows, queue; ``bottleneck.run_level_verdict``).
- **Scenario order:** the two decisive scenarios (changeover -50% and a second AVI) are re-run
  under the perturbations most able to move the constraint (filler and AVI speed +/-20%), to see
  whether "changeover reduction beats a second AVI" survives.

    python -m ffdt.experiments.sensitivity     # about 15 min on 16 cores; writes results/ and reports/
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from ffdt.config import LineConfig, apply_overrides
from ffdt.experiments import bottleneck, runner, scenarios, stats

ROOT = Path(__file__).resolve().parents[3]
RESULTS, REPORTS = ROOT / "results", ROOT / "reports"
LABEL = "Simulated, benchmark-parameterized. Not plant data."
LOW, HIGH = 0.8, 1.2


def _stations(cfg: LineConfig, fn: Callable[[dict], dict]) -> dict:
    return {
        "station_overrides": {
            s.name: fn(s.model_dump()) for s in cfg.stations if fn(s.model_dump())
        }
    }


def _scale_failures(key: str, f: float):
    def fn(s: dict) -> dict:
        return {"failures": {**s["failures"], key: s["failures"][key] * f}} if s["failures"] else {}

    return fn


def _scale_minor(f: float):
    def fn(s: dict) -> dict:
        m = s["minor_stops"]
        return {"minor_stops": {**m, "mean_between_min": m["mean_between_min"] * f}} if m else {}

    return fn


# parameter -> (assumption id, plain label, function(cfg, level) -> overrides, levels)
def _params(cfg: LineConfig) -> dict:
    q, qa = cfg.quality.model_dump(), cfg.qa.model_dump()
    batch = [b.model_dump() for b in cfg.schedule]
    return {
        "sublot_n": (
            "A-001",
            "Sub-lot size N (10 / 200 vials)",
            lambda c, x: {"sublot_vials": int(x)},
            (10, 200),  # 500 breaks ADR-001 (buffer of 2,000 vials must hold 10 sub-lots)
        ),
        "minor_stop_interval": (
            "A-037",
            "Time between minor stops",
            lambda c, x: _stations(c, _scale_minor(x)),
            (LOW, HIGH),
        ),
        "buffer": (
            "A-021",
            "Buffer capacity",
            lambda c, x: {"buffer_vials": int(c.buffer_vials * x)},
            (LOW, HIGH),
        ),
        "filler_rate": (
            "A-030",
            "Filler speed",
            lambda c, x: {
                "station_overrides": {"filler": {"rate_vpm": c.station("filler").rate_vpm * x}}
            },
            (LOW, HIGH),
        ),
        "avi_rate": (
            "A-033",
            "AVI speed",
            lambda c, x: {
                "station_overrides": {"avi": {"rate_vpm": c.station("avi").rate_vpm * x}}
            },
            (LOW, HIGH),
        ),
        "mtbf": (
            "A-035",
            "Time between breakdowns (MTBF)",
            lambda c, x: _stations(c, _scale_failures("mtbf_min", x)),
            (LOW, HIGH),
        ),
        "mttr": (
            "A-036",
            "Repair time (MTTR)",
            lambda c, x: _stations(c, _scale_failures("mttr_mean_min", x)),
            (LOW, HIGH),
        ),
        "changeover": (
            "A-038",
            "Changeover durations",
            lambda c, x: {"changeovers": {"scale": c.changeovers.scale * x}},
            (LOW, HIGH),
        ),
        "batch_size": (
            "A-039",
            "Batch size (6 batches; total volume moves with it)",
            lambda c, x: {
                "schedule": [{**b, "size_vials": int(b["size_vials"] * x)} for b in batch]
            },
            (LOW, HIGH),
        ),
        "false_reject": (
            "A-040",
            "AVI false-reject rate",
            lambda c, x: {
                "quality": {**q, "avi_false_reject_frac": q["avi_false_reject_frac"] * x}
            },
            (LOW, HIGH),
        ),
        "defect_incidence": (
            "A-040",
            "Defect incidence",
            lambda c, x: {"quality": {**q, "defect_frac": q["defect_frac"] * x}},
            (LOW, HIGH),
        ),
        "qa_review": (
            "A-042",
            "QA review time (lead time only)",
            lambda c, x: {"qa": {**qa, "review_mean_min": qa["review_mean_min"] * x}},
            (LOW, HIGH),
        ),
    }


ORDER_CHECK = ["filler_rate", "avi_rate"]
ORDER_SCENARIOS = ["sc04_changeover_m50", "sc01_avi_plus1"]
METRICS = ["good_per_ppt_hour", "line_oee", "mean_lead_time_h"]


def configs() -> list[dict]:
    """Every perturbed configuration: name, parameter, level, config."""
    base = scenarios.baseline_scenario().config
    out = []
    for key, (aid, label, fn, levels) in _params(base).items():
        for lv in levels:
            cfg = apply_overrides(base, fn(base, lv))
            out.append(
                {
                    "name": f"{key}@{lv:g}",
                    "param": key,
                    "assumption": aid,
                    "label": label,
                    "level": lv,
                    "config": cfg,
                }
            )
    return out


def _run(cfg: LineConfig, exp: dict) -> dict:
    r = runner.run(cfg, n_reps=exp["n_reps"], seed=exp["seed"], n_jobs=-1)
    v = bottleneck.run_level_verdict(bottleneck.run_level_picks(r.stations, r.queues))
    return {"summary": r.summary.set_index("replication").sort_index(), "bottleneck": v}


def run_all() -> dict:
    exp = runner.load_experiment()
    base_sc = scenarios.baseline_scenario()
    base = _run(base_sc.config, exp)
    rows, flips = [], []
    runs = {}
    for c in configs():
        r = _run(c["config"], exp)
        runs[c["name"]] = r
        for m in METRICS:
            p = stats.paired(base["summary"][m], r["summary"][m], n_boot=1000)
            rows.append(
                {
                    "name": c["name"],
                    "param": c["param"],
                    "assumption": c["assumption"],
                    "label": c["label"],
                    "level": c["level"],
                    "metric": m,
                    "base": p.base_mean,
                    "diff": p.mean_diff,
                    "ci_low": p.ci_low,
                    "ci_high": p.ci_high,
                    "rel_diff": p.mean_diff / p.base_mean,
                    "bottleneck": r["bottleneck"]["consensus"],
                    "bottleneck_methods_agreeing_of_3": r["bottleneck"]["methods_agreeing"],
                }
            )
        if r["bottleneck"]["consensus"] != base["bottleneck"]["consensus"]:
            flips.append({"name": c["name"], "to": r["bottleneck"]["consensus"]})
    table = pd.DataFrame(rows)
    # scenario-order check: scenario effects re-estimated around perturbed baselines
    order = []
    all_sc = {s.name: s for s in scenarios.all_scenarios()}
    for c in [c for c in configs() if c["param"] in ORDER_CHECK]:
        pb = runs[c["name"]]["summary"]["good_per_ppt_hour"]
        effects = {}
        for sname in ORDER_SCENARIOS:
            over = _scenario_overrides(all_sc[sname])
            scfg = apply_overrides(c["config"], over)
            s = _run(scfg, exp)
            p = stats.paired(pb, s["summary"]["good_per_ppt_hour"], n_boot=1000)
            effects[sname] = {
                "rel_diff": p.mean_diff / p.base_mean,
                "ci_low": p.ci_low / p.base_mean,
                "ci_high": p.ci_high / p.base_mean,
                "bottleneck": s["bottleneck"]["consensus"],
            }
        order.append(
            {
                "perturbation": c["name"],
                "label": c["label"],
                "level": c["level"],
                "effects": effects,
                "smed_beats_avi": bool(
                    effects["sc04_changeover_m50"]["ci_low"] > effects["sc01_avi_plus1"]["ci_high"]
                ),
            }
        )
    RESULTS.mkdir(exist_ok=True)
    table.to_csv(RESULTS / "sensitivity_table.csv", index=False)
    out = {
        "label": LABEL,
        "number_type": "RESULT",
        "n_reps": exp["n_reps"],
        "seed": exp["seed"],
        "baseline_bottleneck": base["bottleneck"]["consensus"],
        "bottleneck_flips": flips,
        "scenario_order": order,
        "table": json.loads(table.to_json(orient="records", double_precision=6)),
    }
    text = json.dumps(out, indent=2, default=lambda o: o.item())  # numpy scalars -> Python
    (RESULTS / "sensitivity.json").write_text(text + "\n", encoding="utf-8")
    return out


LOW_COLOR, HIGH_COLOR, MUTED = "#2a78d6", "#eb6834", "#52514e"  # validated categorical pair


def _level_name(param: str, level: float) -> str:
    if param == "sublot_n":
        return f"N = {level:g}"
    return f"{(level - 1) * 100:+.0f}%"


def tornado(d: dict, metric: str, title: str, unit: str, scale: float, path: Path):
    """Horizontal tornado: one row per parameter, low and high level as two series."""
    import plotly.graph_objects as go

    from ffdt import viz

    t = pd.DataFrame(d["table"]).query("metric == @metric").copy()
    # % = relative to the baseline mean; otherwise absolute (OEE fraction x 100 = points)
    base = t["base"] if unit == "%" else 1.0
    t["eff"] = t["diff"] * scale / base
    t["lo"] = t["ci_low"] * scale / base
    t["hi"] = t["ci_high"] * scale / base
    order = t.groupby("label")["eff"].apply(lambda x: x.abs().max()).sort_values().index.tolist()
    fig = go.Figure()
    for which, color, name in (
        (0, LOW_COLOR, "Lower level (-20%; N = 10)"),
        (1, HIGH_COLOR, "Higher level (+20%; N = 200)"),
    ):
        g = t.sort_values("level").groupby("label").nth(which).set_index("label").loc[order]
        fig.add_bar(
            y=order,
            x=g["eff"],
            orientation="h",
            name=name,
            marker=dict(color=color, cornerradius=4),
            error_x=dict(
                type="data",
                symmetric=False,
                array=g["hi"] - g["eff"],
                arrayminus=g["eff"] - g["lo"],
                color=MUTED,
                thickness=1.2,
                width=3,
            ),
            customdata=[_level_name(p, lv) for p, lv in zip(g["param"], g["level"], strict=True)],
            hovertemplate="%{y} at %{customdata}: %{x:+.2f}" + unit + "<extra></extra>",
        )
    viz._layout(fig, title, 520)
    fig.update_layout(
        barmode="group",
        bargroupgap=0.08,
        template="plotly_white",
        plot_bgcolor="#fcfcfb",
        paper_bgcolor="#fcfcfb",
        legend=dict(orientation="h", y=-0.14, x=0),
    )
    fig.update_traces(opacity=0.95)
    fig.add_vline(x=0, line=dict(color=MUTED, width=1))
    fig.update_xaxes(
        title=f"Change vs baseline v1.0 ({unit.strip()}), paired 95% CI",
        ticksuffix="%" if unit == "%" else "",
    )
    fig.write_image(path, scale=2, width=860)
    return fig


def report(d: dict) -> str:
    t = pd.DataFrame(d["table"])
    g = t[t.metric == "good_per_ppt_hour"].copy()
    o = t[t.metric == "line_oee"].copy()
    top = g.assign(a=g.rel_diff.abs()).sort_values("a", ascending=False)
    by_param = top.groupby("label", sort=False)["a"].max()
    n = g[g.param == "sublot_n"].set_index("level")
    flips = d["bottleneck_flips"]
    order = d["scenario_order"]
    survive = all(x["smed_beats_avi"] for x in order)
    lines = [
        "# Sensitivity analysis",
        "",
        f"Ticket T5.2.2. **{d['label']}** Every number is a RESULT from `results/sensitivity.json` "
        "(`python -m ffdt.experiments.sensitivity`). One parameter at a time is moved to -20% and "
        "+20% of its baseline v1.0 value (sub-lot size N to 10 and 200 vials), with "
        f"{d['n_reps']} replications each, paired with the baseline replications (common random "
        "numbers). Figures: `reports/figures/tornado_throughput.png`, "
        "`reports/figures/tornado_oee.png`.",
        "",
        "Deviation from plan: N = 500 was planned, but ADR-001 requires each 2,000-vial buffer to "
        "hold at least 10 sub-lots, so 200 is the largest valid level without also changing the "
        "buffers.",
        "",
        "## Which parameters matter (good vials per scheduled hour)",
        "| Parameter | Assumption | Level | Change (95% CI) | Line OEE change, points | "
        "Bottleneck |",
        "|---|---|---|---|---|---|",
    ]
    oi = o.set_index("name")
    for label in by_param.index:
        for r in g[g.label == label].sort_values("level").itertuples():
            ro = oi.loc[r.name]
            lines.append(
                f"| {label} | {r.assumption} | {_level_name(r.param, r.level)} | "
                f"{100 * r.rel_diff:+.1f}% ({100 * r.ci_low / r.base:+.1f} to "
                f"{100 * r.ci_high / r.base:+.1f}) | {100 * ro['diff']:+.1f} | {r.bottleneck} |"
            )
    big = [lb for lb, a in by_param.items() if a >= 0.03]
    small = [lb for lb, a in by_param.items() if a < 0.01]
    lines += [
        "",
        "## What survives and what does not",
        f"- **The constraint.** {'The ' + d['baseline_bottleneck'] + ' stays the constraint under every perturbation (three run-level methods).' if not flips else 'The constraint moves under: ' + ', '.join(f['name'] + ' (to ' + f['to'] + ')' for f in flips) + '.'}",
        f"- **The main recommendation.** Changeover reduction beats a second AVI machine "
        f"{'under every' if survive else 'NOT under every'} perturbation of filler and AVI speed "
        "(the parameters most able to move the constraint):",
    ]
    for x in order:
        e = x["effects"]
        s, a = e["sc04_changeover_m50"], e["sc01_avi_plus1"]
        lines.append(
            f"  - {x['label']} {_level_name('', x['level'])}: changeover -50% "
            f"{100 * s['rel_diff']:+.1f}% vs second AVI {100 * a['rel_diff']:+.1f}% "
            f"(95% CI {100 * a['ci_low']:+.1f} to {100 * a['ci_high']:+.1f}); "
            f"constraint with the second AVI: {a['bottleneck']}."
        )
    gi = g.set_index("name")
    opposite = [
        (nm, gi.loc[nm, "label"], gi.loc[nm, "param"], gi.loc[nm, "level"])
        for nm in gi.index
        if abs(gi.loc[nm, "rel_diff"]) >= 0.01
        and (gi.loc[nm, "rel_diff"] > 0) != (oi.loc[nm, "diff"] > 0)
    ]
    for label in dict.fromkeys(lb for _, lb, _, _ in opposite):
        parts = [
            f"at {_level_name(p, lv)} output {100 * gi.loc[nm, 'rel_diff']:+.1f}% but line OEE "
            f"{100 * oi.loc[nm, 'diff']:+.1f} points"
            for nm, lb, p, lv in opposite
            if lb == label
        ]
        lines.append(
            f"- **OEE and output move in opposite directions for {label}:** {'; '.join(parts)}. "
            "Line OEE is measured against the filler's own nominal speed (D4), so changing that "
            "speed moves the yardstick. Compare options on output, not on OEE alone."
        )
    lines += [
        f"- **Parameters that move throughput by 3% or more** at ±20%: "
        f"{', '.join(big) if big else 'none'}. These are where real line data would matter most.",
        f"- **Parameters that move it by less than 1%:** {', '.join(small) if small else 'none'}.",
        f"- **Discretization (sub-lot size N).** N = 10 changes throughput by "
        f"{100 * n.loc[10, 'rel_diff']:+.2f}% and N = 200 by {100 * n.loc[200, 'rel_diff']:+.2f}% "
        "against the default N = 100.",
        "",
        "## Caveats",
        "- One-at-a-time ±20% shows local sensitivity around the baseline; it does not show "
        "interactions between parameters.",
        "- Batch size ±20% keeps 6 batches, so total weekly volume moves with it; good vials per "
        "scheduled hour is a rate, so it stays comparable.",
        "- QA review time affects batch lead time only; it is included for completeness and "
        "cannot move OEE or throughput (QA never blocks the line, A-014).",
        "",
    ]
    return "\n".join(lines)


def write_report(d: dict | None = None) -> None:
    d = d or json.loads((RESULTS / "sensitivity.json").read_text(encoding="utf-8"))
    figs = REPORTS / "figures"
    tornado(
        d,
        "good_per_ppt_hour",
        "Sensitivity of good vials per scheduled hour (±20%, one at a time)",
        "%",
        100.0,
        figs / "tornado_throughput.png",
    )
    tornado(
        d,
        "line_oee",
        "Sensitivity of line OEE (±20%, one at a time)",
        " points",
        100.0,
        figs / "tornado_oee.png",
    )
    (REPORTS / "sensitivity.md").write_text(report(d), encoding="utf-8")


def _scenario_overrides(sc) -> dict:
    import yaml

    with open(sc.path, encoding="utf-8") as f:
        return yaml.safe_load(f)["overrides"]


if __name__ == "__main__":
    import sys

    d = None if "--report-only" in sys.argv else run_all()
    write_report(d)
    d = d or json.loads((RESULTS / "sensitivity.json").read_text(encoding="utf-8"))
    print("flips:", d["bottleneck_flips"])
    for o in d["scenario_order"]:
        print(
            o["perturbation"],
            o["smed_beats_avi"],
            {k: round(v["rel_diff"], 4) for k, v in o["effects"].items()},
        )

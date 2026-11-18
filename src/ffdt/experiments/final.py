"""Final results (T5.2.5): reports/results_final.json and the plant-manager memo.

``results_final.json`` is the **only** source for numbers in the README, slides and resume
bullets. It is built from the scenario run files (results/), the paired comparison
(results/comparison.csv), the bottleneck verdicts (results/bottleneck_*) and the baseline report
(reports/results_baseline.json). ``reports/scenario_findings.md`` is rendered from the JSON, so
every number in the memo is a value in that file.

    python -m ffdt.experiments.final       # rebuild both (after scenarios, stats, bottleneck)
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ffdt.experiments import runner, stats

ROOT = Path(__file__).resolve().parents[3]
RESULTS, REPORTS = ROOT / "results", ROOT / "reports"
LABEL = "Simulated, benchmark-parameterized. Not plant data."

PLAIN = {
    "sc01_avi_plus1": "Add a second AVI machine",
    "sc02_batch_x0p5": "Halve batch size (12 x 50,000 vials)",
    "sc02_batch_x2": "Merge identical neighbouring batches (4 batches)",
    "sc03_inspector_minus1": "One fewer manual inspector",
    "sc03_inspector_plus1": "One more manual inspector",
    "sc03_mechanic_plus1": "One more mechanic",
    "sc03_operator_minus1": "One fewer line operator",
    "sc03_operator_plus1": "One more line operator",
    "sc04_changeover_m25": "Cut every changeover by 25% (SMED, ASSUMPTION)",
    "sc04_changeover_m50": "Cut every changeover by 50% (SMED, ASSUMPTION)",
    "sc05_combo_co50_avi2": "Changeover -50% plus second AVI (exploratory)",
}


def _t(name: str, kind: str) -> pd.DataFrame:
    return pd.read_parquet(RESULTS / name / f"{name}.{kind}.parquet")


def _ci(r: stats.Paired, scale: float = 1.0) -> dict:
    return {
        "base": r.base_mean * scale,
        "diff": r.mean_diff * scale,
        "ci_low": r.ci_low * scale,
        "ci_high": r.ci_high * scale,
        "p": r.p,
    }


def _paired(a: pd.Series, b: pd.Series, scale: float = 1.0) -> dict:
    return _ci(stats.paired(a.sort_index(), b.sort_index()), scale)


def _summary(name: str, col: str) -> pd.Series:
    return _t(name, "summary").set_index("replication")[col]


def _station(name: str, station: str, col: str) -> pd.Series:
    s = _t(name, "stations").query("station == @station").set_index("replication")
    return s[col] / s["ppt_min"] if col.endswith("_min") and col != "ppt_min" else s[col]


def _queue_wait(name: str, buffer: str) -> pd.Series:
    q = _t(name, "queues").query("buffer == @buffer").set_index("replication")
    return q["mean_wait_min"]


def evidence() -> dict:
    """Extra paired quantities named in the pre-registered hypotheses."""
    fill = {
        s: _t(s, "stations").query("station == 'filler'").mean(numeric_only=True)
        for s in ("baseline", "sc04_changeover_m25", "sc04_changeover_m50")
    }
    acct = {}
    for s in ("sc04_changeover_m25", "sc04_changeover_m50"):
        saved = {
            k: float(fill["baseline"][f"{k}_min"] - fill[s][f"{k}_min"])
            for k in ("CHANGEOVER", "BLOCKED", "STARVED", "RUN")
        }
        ppt_saved = float(fill["baseline"]["ppt_min"] - fill[s]["ppt_min"])
        acct[s] = {
            "filler_ppt_saved_min": ppt_saved,
            "filler_changeover_saved_min": saved["CHANGEOVER"],
            "filler_blocked_saved_min": saved["BLOCKED"],
            "filler_starved_saved_min": saved["STARVED"],
            "filler_run_change_min": -saved["RUN"],
            "ratio_ppt_saved_to_own_changeover_saved": ppt_saved / saved["CHANGEOVER"],
        }
    cart = {
        s: float((_station(s, "cartoner", "WAIT_STAFF_min")).mean())
        for s in ("baseline", "sc03_operator_plus1", "sc03_operator_minus1")
    }
    return {
        "H1b_queue_wait_before_avi_min": _paired(
            _queue_wait("baseline", "in:avi"), _queue_wait("sc01_avi_plus1", "in:avi")
        ),
        "H1b_queue_wait_before_manual_inspection_min": _paired(
            _queue_wait("baseline", "in:manual_inspection"),
            _queue_wait("sc01_avi_plus1", "in:manual_inspection"),
        ),
        **{
            f"H2b_{s}_{m}": _paired(_summary("baseline", m), _summary(s, m))
            for s in ("sc02_batch_x0p5", "sc02_batch_x2")
            for m in ("mean_cycle_time_h", "mean_qa_queue_h", "mean_lead_time_h")
        },
        "H3a_wait_staff_share_by_station_baseline": {
            st: float(_station("baseline", st, "WAIT_STAFF_min").mean())
            for st in ("filler", "avi", "labeler", "cartoner")
        },
        "H3a_cartoner_wait_staff_share": cart,
        "H4a_filler_minute_accounting": acct,
        "H5_combo_vs_sc04_m50_good_per_ppt_hour": _paired(
            _summary("sc04_changeover_m50", "good_per_ppt_hour"),
            _summary("sc05_combo_co50_avi2", "good_per_ppt_hour"),
        ),
    }


def scenario_rows(comp: pd.DataFrame) -> list[dict]:
    rows = []
    prim = comp[comp["primary"]]
    sec = comp.set_index(["scenario", "metric"])
    for r in prim.itertuples():
        b = r.base_mean
        rows.append(
            {
                "scenario": r.scenario,
                "plain_name": PLAIN[r.scenario],
                "family": r.family,
                "set": r.set,
                "good_per_ppt_hour_diff": r.mean_diff,
                "pct_diff": r.mean_diff / b,
                "pct_ci_low": r.ci_low / b,
                "pct_ci_high": r.ci_high / b,
                "p": r.p,
                "p_holm": None if pd.isna(r.p_holm) else r.p_holm,
                "practical": bool(r.practical),
                "bootstrap_agrees": bool(r.boot_agrees),
                "paired_half_width": r.paired_half_width,
                "unpaired_half_width": r.unpaired_half_width,
                "oee_points_diff": 100 * sec.loc[(r.scenario, "line_oee"), "mean_diff"],
                "changeover_share_points_diff": 100
                * sec.loc[(r.scenario, "changeover_share"), "mean_diff"],
                "lead_time_h_diff": sec.loc[(r.scenario, "mean_lead_time_h"), "mean_diff"],
                "lead_time_h_ci": [
                    sec.loc[(r.scenario, "mean_lead_time_h"), "ci_low"],
                    sec.loc[(r.scenario, "mean_lead_time_h"), "ci_high"],
                ],
            }
        )
    return sorted(rows, key=lambda d: -d["pct_diff"])


def hypotheses(ev: dict, sc: dict, bn: dict, base: dict) -> dict:
    """Verdicts against the pre-registered refutation conditions (scenario_hypotheses.md)."""
    acc = ev["H4a_filler_minute_accounting"]
    c = ev["H3a_cartoner_wait_staff_share"]
    return {
        "H1a": {
            "verdict": "supported",
            "why": f"AVI is not the constraint ({bn['constraint']} is, all 4 methods) and a second "
            f"AVI gives {100 * sc['sc01_avi_plus1']['pct_diff']:+.1f}% "
            f"(95% CI {100 * sc['sc01_avi_plus1']['pct_ci_low']:+.1f} to "
            f"{100 * sc['sc01_avi_plus1']['pct_ci_high']:+.1f}%), not significant.",
        },
        "H1b": {
            "verdict": "mixed",
            "why": "Queue wait before AVI falls "
            f"{-ev['H1b_queue_wait_before_avi_min']['diff']:.1f} min; the queue before manual "
            f"re-inspection rises {60 * ev['H1b_queue_wait_before_manual_inspection_min']['diff']:.0f}"
            " s (negligible, but opposite in direction).",
        },
        "H2a": {
            "verdict": "supported",
            "why": f"Larger batches {100 * sc['sc02_batch_x2']['pct_diff']:+.1f}%, smaller "
            f"{100 * sc['sc02_batch_x0p5']['pct_diff']:+.1f}%; baseline changeover share "
            f"{100 * base['changeover_share']:.0f}% of PPT, well above the 5% floor.",
        },
        "H2b": {
            "verdict": "refuted as stated: not monotonic",
            "why": "Lead time rises at both levels. Merging batches adds cycle time "
            f"({ev['H2b_sc02_batch_x2_mean_cycle_time_h']['diff']:+.1f} h); halving batches cuts "
            f"cycle time ({ev['H2b_sc02_batch_x0p5_mean_cycle_time_h']['diff']:+.1f} h) but QA "
            f"release queueing grows {ev['H2b_sc02_batch_x0p5_mean_qa_queue_h']['diff']:+.1f} h, "
            "so QA release becomes the lead-time constraint.",
        },
        "H3a": {
            "verdict": "refuted as registered",
            "why": "Wait-for-staff at the filler is "
            f"{100 * ev['H3a_wait_staff_share_by_station_baseline']['filler']:.2f}% of PPT, yet "
            f"+1 operator gives {100 * sc['sc03_operator_plus1']['pct_diff']:+.1f}%. The waits sit "
            f"downstream: cartoner {100 * c['baseline']:.1f}% of its PPT "
            f"({100 * c['sc03_operator_plus1']:.1f}% with +1 operator). The pre-registered test "
            "measured staff waits at the wrong station.",
        },
        "H3b": {"verdict": "not testable", "why": "-1 mechanic means zero mechanics (A4)."},
        "H4a": {
            "verdict": "monotonic: supported; less than proportional: refuted, mechanism found",
            "why": "Filler run time is unchanged; its scheduled time falls "
            f"{acc['sc04_changeover_m50']['filler_ppt_saved_min']:.0f} min at -50%, "
            f"{acc['sc04_changeover_m50']['ratio_ppt_saved_to_own_changeover_saved']:.2f}x its own "
            f"changeover saving ({acc['sc04_changeover_m50']['filler_changeover_saved_min']:.0f} "
            "min), because shorter downstream changeovers also cut the filler's blocked time "
            f"({acc['sc04_changeover_m50']['filler_blocked_saved_min']:.0f} min). The minute "
            "accounting reconciles, so this is not an accounting error.",
        },
        "H4b": {"verdict": "not examined", "why": "No small-batch x SMED scenario was registered."},
        "H5": {
            "verdict": "supported (exploratory)",
            "why": "AVI is not the constraint and the combination adds only "
            f"{100 * ev['H5_combo_vs_sc04_m50_good_per_ppt_hour']['diff'] / ev['H5_combo_vs_sc04_m50_good_per_ppt_hour']['base']:+.1f}%"
            " over changeover -50% alone (below the 3% practical threshold).",
        },
    }


def verification() -> dict:
    """Analytical cross-checks (same seeded runs as docs/verification.md) and the test count."""
    import subprocess
    import sys

    from ffdt.experiments import analytic

    checks = [analytic.mm1_wait(), analytic.mm1k_block(), analytic.availability()]
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-m", ""],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    # addopts already has -q, so -q again prints "path: count" per file; -m "" includes slow
    n_tests = sum(int(ln.rsplit(":", 1)[1]) for ln in out.splitlines() if ln.startswith("tests"))
    return {
        "automated_tests": n_tests,
        "analytic_checks": [
            {
                "name": c.name,
                "theory": c.theory,
                "simulated": c.mean,
                "ci": [c.ci_low, c.ci_high],
                "rel_error": c.rel_error,
                "theory_in_ci": c.theory_in_ci,
            }
            for c in checks
        ],
        "max_abs_rel_error": max(abs(c.rel_error) for c in checks),
        "all_theory_in_ci": all(c.theory_in_ci for c in checks),
    }


def sensitivity_summary() -> dict | None:
    """Conclusions of the one-at-a-time sensitivity analysis (T5.2.2), added 2026-11-18."""
    f = RESULTS / "sensitivity.json"
    if not f.exists():
        return None
    d = json.loads(f.read_text(encoding="utf-8"))
    t = pd.DataFrame(d["table"]).query("metric == 'good_per_ppt_hour'")
    by = t.assign(a=t["rel_diff"].abs()).groupby("label")["a"].max().sort_values(ascending=False)
    n = t[t["param"] == "sublot_n"]["rel_diff"].abs().max()
    avi = [x["effects"]["sc01_avi_plus1"]["rel_diff"] for x in d["scenario_order"]]
    smed = [x["effects"]["sc04_changeover_m50"]["rel_diff"] for x in d["scenario_order"]]
    return {
        "source": "results/sensitivity.json, reports/sensitivity.md",
        "n_perturbations": int(t["name"].nunique()),
        "constraint_unchanged_in_all": not d["bottleneck_flips"],
        "smed_beats_second_avi_in_all_speed_perturbations": all(
            x["smed_beats_avi"] for x in d["scenario_order"]
        ),
        "smed_m50_range": [min(smed), max(smed)],
        "second_avi_range": [min(avi), max(avi)],
        "largest_effects_pct": {k: float(v) for k, v in by.head(3).items()},
        "max_discretization_effect": float(n),
    }


def build() -> dict:
    comp = pd.read_csv(RESULTS / "comparison.csv")
    ver = pd.read_csv(RESULTS / "bottleneck_verdicts.csv").set_index("scenario")
    bev = pd.read_parquet(RESULTS / "bottleneck_evidence.parquet").query("scenario == 'baseline'")
    base_json = json.loads((REPORTS / "results_baseline.json").read_text(encoding="utf-8"))
    rows = scenario_rows(comp)
    sc = {r["scenario"]: r for r in rows}
    b = bev.groupby("station")[["sole_share", "shifting_share"]].mean()
    second = (
        bev.groupby("replication")
        .apply(lambda g: g.set_index("station")["active_period_share"].nlargest(2).index[1])
        .value_counts()
    )
    bn = {
        "constraint": ver.loc["baseline", "consensus"],
        "methods_agreeing_of_4": int(ver.loc["baseline", "methods_agreeing"]),
        "constraint_utilization": float(
            bev.groupby("station")["utilization"].mean()[ver.loc["baseline", "consensus"]]
        ),
        "constraint_sole_share": float(b.loc[ver.loc["baseline", "consensus"], "sole_share"]),
        "secondary": second.index[0],
        "secondary_reps": int(second.iloc[0]),
        "secondary_sole_plus_shifting_share": float(b.loc[second.index[0]].sum()),
        "scenarios_shifting_constraint": [
            s for s in ver.index if ver.loc[s, "shifts_from_baseline"]
        ],
    }
    ln = base_json["line"]
    par = {r["category"]: r for r in base_json["loss_pareto"]}
    base = {
        "line_oee": ln["line_oee"],
        "good_per_ppt_hour": ln["good_per_ppt_hour"],
        "makespan_h": ln["makespan_h"],
        "mean_lead_time_h": ln["mean_lead_time_h"],
        "changeover_share": par["CHANGEOVER"]["mean"],
        "blocked_share": par["BLOCKED"]["mean"],
        "n_reps": base_json["n_reps"],
        "config_hash": base_json["config_hash"],
        "seed": base_json["root_seed"],
    }
    ev = evidence()
    # CRN narrowing only for levers that move output (as in notebook 06); where the paired
    # difference is ~0 in every replication the ratio is degenerate and not meaningful
    changing = [r for r in rows if abs(r["pct_diff"]) >= 0.001]
    crn = [r["unpaired_half_width"] / r["paired_half_width"] for r in changing]
    return {
        "label": LABEL,
        "number_type": "RESULT",
        "frozen": "2026-11-18",
        "git_sha_at_build": runner.git_sha(ROOT),
        "sources": {
            "baseline": "reports/results_baseline.json",
            "scenarios": "results/<scenario>/*.parquet (python tasks.py scenarios)",
            "comparison": "results/comparison.csv (python -m ffdt.experiments.stats)",
            "bottleneck": "results/bottleneck_verdicts.csv (python -m ffdt.experiments.bottleneck)",
            "preregistration": "docs/scenario_matrix.md, docs/domain/scenario_hypotheses.md",
        },
        "practical_threshold": "TARGET: +3% good vials per PPT hour or +2 OEE points",
        "baseline": base,
        "bottleneck": bn,
        "scenarios": rows,
        "crn_ci_narrowing_x": {
            "min": min(crn),
            "max": max(crn),
            "scenarios": [r["scenario"] for r in changing],
            "rule": "scenarios whose mean effect is at least 0.1% of baseline output",
        },
        "verification": verification(),
        "sensitivity": sensitivity_summary(),
        "hypothesis_evidence": ev,
        "hypotheses": hypotheses(ev, sc, bn, base),
        "errata": {
            "E1": "Parallel AVI units let a batch's last sub-lot overtake; fixed, sc01/sc05 re-run",
            "E2": "Station reject counts logged after the quality transform; fixed, no effect on "
            "line metrics or scenario results",
        },
    }


# -- memo --------------------------------------------------------------------------------------
def _p(x: float, nd: int = 1) -> str:
    v = round(100 * x, nd)
    return f"{v + 0.0:+.{nd}f}%"  # + 0.0 turns -0.0 into 0.0


def _h(x: float) -> str:
    v = round(x, 1)
    return f"{v + 0.0:+.1f} h"


def _holm(p: float | None) -> str:
    return "n/a" if p is None else ("<0.001" if p < 0.001 else f"{p:.2f}")


def memo(d: dict) -> str:
    b, bn, sc = d["baseline"], d["bottleneck"], {r["scenario"]: r for r in d["scenarios"]}
    h, ev = d["hypotheses"], d["hypothesis_evidence"]
    main = [r for r in d["scenarios"] if r["set"] == "main"]
    lines = [
        "# Fill-finish line: what limits output and what to do first",
        "",
        f"*Memo for the plant manager · {LABEL} Every number is a RESULT from "
        "`reports/results_final.json` (frozen "
        f"{d['frozen']}); its `sources` block names the run files. Baseline v1.0, "
        f"{b['n_reps']} replications per scenario, common random numbers.*",
        "",
        "## Bottom line",
        f"- **The filler is the constraint.** All {bn['methods_agreeing_of_4']} bottleneck methods "
        f"agree, and no scenario tested moves it. It is the sole bottleneck "
        f"{100 * bn['constraint_sole_share']:.0f}% of scheduled time; the {bn['secondary']} is a "
        f"secondary, shifting bottleneck (in {bn['secondary_reps']} of {b['n_reps']} runs).",
        f"- **Changeovers are the biggest loss:** {100 * b['changeover_share']:.0f}% of the "
        f"filler's scheduled time. Line OEE is {100 * b['line_oee']['mean']:.0f}% "
        f"(95% CI {100 * b['line_oee']['ci_low']:.1f} to {100 * b['line_oee']['ci_high']:.1f}).",
        f"- **Do first: a SMED changeover-reduction project.** A 25% cut gives "
        f"{_p(sc['sc04_changeover_m25']['pct_diff'])} good vials per scheduled hour, 50% gives "
        f"{_p(sc['sc04_changeover_m50']['pct_diff'])}. The reduction levels are assumptions, not "
        "measured SMED results.",
        f"- **Do not buy a second AVI machine for output:** "
        f"{_p(sc['sc01_avi_plus1']['pct_diff'])}, not significant. AVI is not the constraint.",
        "",
        "## Ranked options (main pre-registered set, Holm-adjusted)",
        "Change in good vials per scheduled-production hour vs baseline "
        f"({b['good_per_ppt_hour']['mean']:,.0f}/h), paired 95% CI. Practical significance is a "
        "TARGET of +3%.",
        "",
        "| Rank | Option | Effect (95% CI) | Holm p | Practical? | Batch lead time |",
        "|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(main, 1):
        pr = "yes" if r["practical"] else "no"
        lines.append(
            f"| {i} | {r['plain_name']} | {_p(r['pct_diff'])} ({_p(r['pct_ci_low'])} to "
            f"{_p(r['pct_ci_high'])}) | {_holm(r['p_holm'])} | {pr} | {_h(r['lead_time_h_diff'])} |"
        )
    x = sc["sc05_combo_co50_avi2"]
    lines += [
        "",
        f"Exploratory, not adjusted: changeover -50% plus a second AVI gives {_p(x['pct_diff'])}, "
        "only "
        f"{_p(ev['H5_combo_vs_sc04_m50_good_per_ppt_hour']['diff'] / ev['H5_combo_vs_sc04_m50_good_per_ppt_hour']['base'])}"
        " more than changeover -50% alone.",
        "",
        "## What to do, in order",
        f"1. **SMED on the line changeover.** It attacks the constraint's largest loss. Shorten "
        f"changeovers at every station, not only the filler: at -50% the filler's scheduled time falls "
        f"{ev['H4a_filler_minute_accounting']['sc04_changeover_m50']['ratio_ppt_saved_to_own_changeover_saved']:.2f}x"
        " as much as its own changeover time does, because shorter downstream changeovers stop "
        "blocking it.",
        f"2. **Add one line operator** ({_p(sc['sc03_operator_plus1']['pct_diff'])}). Operator "
        "waits are concentrated at the packaging end: the cartoner waits for staff "
        f"{100 * ev['H3a_cartoner_wait_staff_share']['baseline']:.0f}% of its scheduled time. Do "
        f"not cut one ({_p(sc['sc03_operator_minus1']['pct_diff'])}).",
        f"3. **Keep batches large where the schedule allows.** Merging identical neighbouring "
        f"batches gives {_p(sc['sc02_batch_x2']['pct_diff'])} but adds "
        f"{sc['sc02_batch_x2']['lead_time_h_diff']:.1f} h of batch lead time. Halving batches "
        f"changes output by {_p(sc['sc02_batch_x0p5']['pct_diff'])} and adds "
        f"{sc['sc02_batch_x0p5']['lead_time_h_diff']:.1f} h, because QA release queueing grows "
        f"{ev['H2b_sc02_batch_x0p5_mean_qa_queue_h']['diff']:.0f} h.",
        "4. **Not worth it for output:** a second AVI, a mechanic, or an inspector (no "
        "significant effect). They may still be justified for quality or risk reasons this model "
        "does not value.",
        "",
        "## What the study got wrong in advance (pre-registered hypotheses)",
        f"- H3a ({h['H3a']['verdict']}): {h['H3a']['why']}",
        f"- H2b ({h['H2b']['verdict']}): {h['H2b']['why']}",
        f"- H4a ({h['H4a']['verdict']}): {h['H4a']['why']}",
        "- Supported: H1a, H2a, H5 (exploratory). Mixed: H1b. Not testable: H3b. Not examined: "
        "H4b. Full list in `reports/results_final.json`.",
        "",
        "## Limitations",
        "- **Simulated, benchmark-parameterized.** Speeds, failure and changeover times come from "
        "public benchmarks and engineering judgment (`data/raw/benchmark_sources.csv`), not from "
        "a plant. Face validation by a practitioner is still pending (T4.2.2).",
        "- **SMED levels are assumptions.** The -25%/-50% levels follow a published case study (up to 50%, source B-021); the "
        "achievable cut on a real line must be measured.",
        "- **One product mix and one week.** Six batches, two products, two vial formats, two "
        "shifts on five days. A different mix or schedule could move the constraint.",
        "- **Out of scope:** lyophilization, sterility-test holds, media fills, deviations. "
        "No costs are modeled, so the ranking is by output, not by return on investment.",
        "- **Two model errata were found and fixed during the study** (E1 parallel AVI units, "
        "E2 station reject counts); both are documented, and all runs were repeated after the "
        "fixes.",
        "",
    ]
    return "\n".join(lines)


def _ci_pct(c: dict, nd: int = 1) -> str:
    return f"{100 * c['ci_low']:.{nd}f}-{100 * c['ci_high']:.{nd}f}%"


def portfolio(d: dict) -> str:
    """docs/portfolio/resume_bullets.md (T7.2.2), rendered from results_final.json."""
    b, bn, v = d["baseline"], d["bottleneck"], d["verification"]
    sc = {r["scenario"]: r for r in d["scenarios"]}
    m50, m25, avi = sc["sc04_changeover_m50"], sc["sc04_changeover_m25"], sc["sc01_avi_plus1"]
    op, x0 = sc["sc03_operator_plus1"], sc["sc02_batch_x0p5"]
    ev, h, crn = d["hypothesis_evidence"], d["hypotheses"], d["crn_ci_narrowing_x"]
    n_main = sum(r["set"] == "main" for r in d["scenarios"])
    oee = b["line_oee"]
    qa = ev["H2b_sc02_batch_x0p5_mean_qa_queue_h"]["diff"]
    cart = ev["H3a_cartoner_wait_staff_share"]["baseline"]
    refuted = [k for k, x in h.items() if "refuted" in x["verdict"]]
    count = {2: "Two", 3: "Three", 4: "Four", 5: "Five"}.get(len(refuted), str(len(refuted)))
    sens = d.get("sensitivity")
    lines = [
        "# Resume bullets, pitch and interview Q&A",
        "",
        "Ticket T7.2.2. Generated by `python -m ffdt.experiments.final` from "
        f"`reports/results_final.json` (frozen {d['frozen']}); do not edit by hand. Every number "
        "is a RESULT from a **simulated, benchmark-parameterized** line, not plant data.",
        "",
        "## Resume bullets",
        f"1. Built a discrete-event simulation (Python, SimPy) of a sterile vial fill-finish line "
        "(washing to cartoning) with random breakdowns, changeovers, shared staff and QA batch "
        f"release, parameterized from published benchmarks; baseline line OEE "
        f"{100 * oee['mean']:.1f}% (95% CI {_ci_pct(oee)}, {b['n_reps']} replications; "
        "simulated).",
        f"2. Identified the {bn['constraint']} as the constraint with {bn['methods_agreeing_of_4']} "
        f"bottleneck methods and changeovers as its largest loss ({100 * b['changeover_share']:.0f}%"
        f" of scheduled time); ranked {n_main} pre-registered scenarios with paired, "
        "Holm-adjusted tests: a 50% changeover cut raised good output "
        f"{100 * m50['pct_diff']:.1f}% (95% CI {_ci_pct({'ci_low': m50['pct_ci_low'], 'ci_high': m50['pct_ci_high']})})"
        f", while a second inspection machine had no significant effect (simulated).",
        "3. Delivered a Streamlit what-if app for non-technical users (batch size, staffing, "
        f"changeover time) backed by {v['automated_tests']} automated tests, including M/M/1, "
        f"M/M/1/K and availability checks within {100 * v['max_abs_rel_error']:.1f}% of theory "
        "(simulated, benchmark-parameterized).",
        "",
        "Project-entry disclosure line: *Simulated line parameterized from public benchmarks; no "
        "plant data.*",
        "",
        "Alternative bullet (process-improvement roles):",
        f"- Showed that staffing, not equipment, was the next lever after changeovers: one more "
        f"line operator added {100 * op['pct_diff']:.1f}% good output because operator waits "
        f"sat at the packaging end ({100 * cart:.0f}% of cartoner time), refuting my own "
        "pre-registered hypothesis (simulated).",
        "",
        "## 60-second pitch (PITCH_WORDS words; read it aloud with a timer, target 75 s or less)",
        "> Sterile fill-finish lines are expensive, and improvements like a second inspection "
        "machine are often justified with averages that ignore queues. I built a simulation of a "
        "vial fill-finish line, with breakdowns, changeovers, staff and QA release, from published "
        "benchmarks, because I had no plant data. I tested it against queueing theory, froze a "
        f"baseline at {100 * oee['mean']:.0f}% OEE, and wrote my hypotheses down before running "
        f"any scenario. The constraint was the {bn['constraint']}, and changeovers ate "
        f"{100 * b['changeover_share']:.0f}% of its time, so cutting changeovers in half gave "
        f"about {100 * m50['pct_diff']:.0f}% more good vials, while a second inspection machine "
        f"did nothing, because inspection was not the constraint. {count} of my own hypotheses "
        "were wrong, and those were the most useful findings: for example, an extra operator "
        "mattered because the waits were at the packaging end. With real data I would fit "
        "downtime from the historian and recalibrate.",
        "",
        "## Interview Q&A (operations hiring manager)",
        "| Question | Talking points |",
        "|---|---|",
        "| What was the bottleneck, and was it stable? | The "
        f"{bn['constraint']}, by utilization, active-period, blocking/starvation and queue methods "
        f"(all {bn['methods_agreeing_of_4']} agree, every scenario). It is the sole bottleneck only "
        f"{100 * bn['constraint_sole_share']:.0f}% of the time: failures and changeovers make it "
        f"shift, and the {bn['secondary']} is a secondary bottleneck. No scenario moved it. |",
        f"| The {bn['constraint']} runs only {100 * bn['constraint_utilization']:.0f}% of "
        "scheduled time. How is it the constraint? | Its lost time is its own changeovers, not "
        "waiting: it is almost never starved or blocked. Utilization alone undersells it, which "
        "is why I used several methods. |",
        f"| Why did a second AVI machine not help? | Theory of Constraints: capacity at a "
        f"non-constraint adds WIP, not output. Result {100 * avi['pct_diff']:+.1f}% "
        f"(CI {100 * avi['pct_ci_low']:+.1f} to {100 * avi['pct_ci_high']:+.1f}%). It did "
        f"shorten the queue in front of AVI by {-ev['H1b_queue_wait_before_avi_min']['diff']:.1f} "
        "min. |",
        f"| How would SMED apply? | Separate internal from external setup. The -25%/-50% levels "
        f"are assumptions from a published case study, not measured; they gave "
        f"{100 * m25['pct_diff']:.1f}% and {100 * m50['pct_diff']:.1f}%. Shorten changeovers at "
        "every station: downstream changeovers also block the filler. |",
        f"| Why not make batches smaller for flexibility? | In the model halving batches cost "
        f"{-100 * x0['pct_diff']:.1f}% output and added {x0['lead_time_h_diff']:.0f} h of lead "
        f"time, because QA release queueing grew {qa:.0f} h. Smaller batches move the lead-time "
        "constraint to QA. |",
        f"| How do you know the simulation is right? | Verification, not validation: "
        f"{v['automated_tests']} tests including vial conservation, state-time accounting and "
        f"analytic checks within {100 * v['max_abs_rel_error']:.1f}% of theory. Validation is face "
        "validity only; no plant data. |",
        f"| Why paired comparisons? | Common random numbers give each scenario the same "
        f"breakdowns as the baseline, so the comparison isolates the change. CIs were "
        f"{crn['min']:.1f}x to {crn['max']:.1f}x narrower than unpaired ones. |",
        f"| Which of your hypotheses were wrong? | {', '.join(refuted)} (refuted in whole or "
        "in part). "
        "For example, I expected staffing to matter only where the filler waited for staff; the "
        "waits were downstream. Pre-registering made that visible instead of letting me "
        "rationalize it. |",
        "| Would the answer change with different assumptions? | "
        + (
            f"I moved {sens['n_perturbations'] // 2} parameters one at a time, two levels each "
            "(±20%): the "
            f"{bn['constraint']} stayed the constraint in every case, and changeover reduction beat "
            f"a second AVI under every filler and AVI speed change "
            f"({100 * sens['smed_m50_range'][0]:.0f}-{100 * sens['smed_m50_range'][1]:.0f}% vs at "
            f"most {100 * sens['second_avi_range'][1]:.1f}%). Filler speed, changeover time and batch "
            "size matter most, so that is where real data would pay off first. |"
            if sens
            else "Sensitivity analysis pending. |"
        ),
        "| Did you find bugs? | Two, both from checks: parallel AVI units let a batch's last "
        "sub-lot overtake (spurious changeovers), and station reject counts were logged after "
        "the quality step. Both were fixed, documented as errata, and every run was repeated. |",
        "| Where did the numbers come from? | A benchmark source table with a confidence grade "
        "per value; judgment values are tagged. With real data I would fit time-to-failure and "
        "repair from the historian or MES and calibrate to measured OEE. |",
        "| What GMP issues touch the model? | Line clearance at changeovers (21 CFR 211.130(e) "
        "for packaging and labeling; fill-area citation is VERIFY), QA batch release, Grade A "
        "interventions (EU GMP Annex 1, clause VERIFY). A model like this is decision support, "
        "not a validated GxP system. |",
        "| What are the limits? | One line, liquid vials, one week and product mix, no "
        "lyophilization, sterility-test holds or deviations, no costs. Ranking is by output, "
        "not ROI. |",
        "",
        "## LinkedIn project entry",
        "**Pharma Fill-Finish Digital Twin (Discrete-Event Simulation).** A simulation of a "
        "sterile vial fill-finish line that finds the bottleneck and ranks improvement options "
        f"with confidence intervals: the {bn['constraint']} limits output, and changeover "
        f"reduction beat adding inspection capacity. *Simulated line parameterized from public "
        "benchmarks; no plant data.* [app link] · [repo link]",
        "",
    ]
    pitch = next(ln for ln in lines if ln.startswith("> "))
    return "\n".join(lines).replace("PITCH_WORDS", str(len(pitch[2:].split())))


PORTFOLIO = ROOT / "docs" / "portfolio" / "resume_bullets.md"
README_TEMPLATE = ROOT / "docs" / "portfolio" / "README.template.md"
README = ROOT / "README.md"


def readme(d: dict, template: str, app_url: str | None = None) -> str:
    """README.md (T7.1.1): fill ``{{name}}`` placeholders in the template from the JSON."""
    import re

    b, bn, v = d["baseline"], d["bottleneck"], d["verification"]
    sc = {r["scenario"]: r for r in d["scenarios"]}
    m50 = sc["sc04_changeover_m50"]
    rows = [
        "| Option | Set | Effect (95% CI) | Holm-adjusted p | Practically significant (size ≥ 3%)? |",
        "|---|---|---|---|---|",
    ]
    for r in d["scenarios"]:
        rows.append(
            f"| {r['plain_name']} | {r['set']} | {_p(r['pct_diff'])} ({_p(r['pct_ci_low'])} to "
            f"{_p(r['pct_ci_high'])}) | {_holm(r['p_holm'])} | {'yes' if r['practical'] else 'no'} |"
        )
    refuted = [k for k, x in d["hypotheses"].items() if "refuted" in x["verdict"]]
    app_line = (
        f"**Try it:** [what-if app]({app_url}) (simulated, benchmark-parameterized)."
        if app_url
        else "**What-if app:** run `python tasks.py app` locally (see How to run); it lets a "
        "non-technical user change batch size, staffing, equipment and changeover time, see OEE, "
        "throughput, losses and queue times, and compare any option with the baseline (paired "
        "95% CIs, bottleneck shift)."
    )
    val = {
        "co_share": f"{100 * b['changeover_share']:.0f}%",
        "blocked_share": f"{100 * b['blocked_share']:.0f}%",
        "m50_pct": f"{100 * m50['pct_diff']:.1f}%",
        "m50_ci": f"{100 * m50['pct_ci_low']:.1f}% to {100 * m50['pct_ci_high']:.1f}%",
        "app_line": app_line,
        "n_reps": str(b["n_reps"]),
        "n_main": str(sum(r["set"] == "main" for r in d["scenarios"])),
        "oee": f"{100 * b['line_oee']['mean']:.1f}%",
        "oee_ci": f"{100 * b['line_oee']['ci_low']:.1f}% to {100 * b['line_oee']['ci_high']:.1f}%",
        "gph": f"{b['good_per_ppt_hour']['mean']:,.0f}",
        "lead": f"{b['mean_lead_time_h']['mean']:.0f}",
        "constraint": bn["constraint"],
        "n_methods": str(bn["methods_agreeing_of_4"]),
        "sole_share": f"{100 * bn['constraint_sole_share']:.0f}%",
        "secondary": bn["secondary"],
        "scenario_table": "\n".join(rows),
        "refuted": ", ".join(refuted[:-1]) + " and " + refuted[-1]
        if len(refuted) > 1
        else "".join(refuted),
        "cart_wait": f"{100 * d['hypothesis_evidence']['H3a_cartoner_wait_staff_share']['baseline']:.0f}%",
        "n_tests": str(v["automated_tests"]),
        "max_err": f"{100 * v['max_abs_rel_error']:.1f}%",
        "sens_line": (
            f"- **Sensitivity** ([`reports/sensitivity.md`](reports/sensitivity.md)): "
            f"{d['sensitivity']['n_perturbations'] // 2} parameters moved one at a time to two "
            f"levels each (mostly ±20%). The {bn['constraint']} stays the constraint in every case, "
            "and changeover reduction beats a second AVI under every filler and AVI speed change. "
            "Filler speed, changeover time and batch size move output most. Sub-lot "
            "discretization changes output by at most "
            f"{100 * d['sensitivity']['max_discretization_effect']:.1f}%."
            if d.get("sensitivity")
            else "- **Sensitivity:** pending."
        ),
    }
    out = re.sub(r"\{\{(\w+)\}\}", lambda m: val[m.group(1)], template)
    if "{{" in out:
        raise ValueError("unfilled placeholder in README template")
    return out


PRESETS = REPORTS / "app_presets.json"
PRESET_METRICS = [
    "good_per_ppt_hour",
    "line_oee",
    "changeover_share",
    "wait_staff_share",
    "mean_lead_time_h",
    "makespan_h",
]


def presets() -> dict:
    """Precomputed scenario comparisons for the app's Compare view (T6.2.1): paired deltas with
    95% CIs per metric and the bottleneck verdict per configuration (30 replications each)."""
    comp = pd.read_csv(RESULTS / "comparison.csv")
    ver = pd.read_csv(RESULTS / "bottleneck_verdicts.csv").set_index("scenario")
    out = {"label": LABEL, "baseline_bottleneck": ver.loc["baseline", "consensus"], "scenarios": {}}
    for name, g in comp.groupby("scenario", sort=False):
        g = g.set_index("metric").loc[PRESET_METRICS]
        out["scenarios"][name] = {
            "plain_name": PLAIN[name],
            "set": g["set"].iloc[0],
            "n_reps": int(g["n"].iloc[0]),
            "bottleneck": ver.loc[name, "consensus"],
            "bottleneck_methods_agreeing_of_4": int(ver.loc[name, "methods_agreeing"]),
            "metrics": {
                m: {
                    "base": float(r.base_mean),
                    "diff": float(r.mean_diff),
                    "ci_low": float(r.ci_low),
                    "ci_high": float(r.ci_high),
                    "p": float(r.p),
                }
                for m, r in g.iterrows()
            },
        }
    return out


def write() -> dict:
    PRESETS.write_text(json.dumps(presets(), indent=2) + "\n", encoding="utf-8")
    d = build()
    (REPORTS / "results_final.json").write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
    (REPORTS / "scenario_findings.md").write_text(memo(d), encoding="utf-8")
    PORTFOLIO.parent.mkdir(parents=True, exist_ok=True)
    PORTFOLIO.write_text(portfolio(d), encoding="utf-8")
    README.write_text(readme(d, README_TEMPLATE.read_text(encoding="utf-8")), encoding="utf-8")
    from ffdt.experiments import economics

    economics.write()
    try:  # needs a headless Chrome or Edge for the PDF; HTML and figures always rebuild
        from ffdt.experiments import slides

        slides.write()
    except (RuntimeError, OSError) as e:
        print(f"slides PDF not printed: {e}")
    return d


if __name__ == "__main__":
    write()
    print((REPORTS / "scenario_findings.md").read_text(encoding="utf-8"))

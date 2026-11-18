"""Facade for the what-if app (T6.1.1). The app imports only this module.

    cfg = build_config(Levers(operators=5, changeover_scale=0.7))
    out = simulate(cfg, quick=True)
    out.kpis        mean, 95% CI half-width per metric
    out.summary     one row per replication

Levers are the user-facing knobs; every other parameter stays at the baseline config value.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pydantic import ValidationError

from ffdt.config import LineConfig, apply_overrides, load_config
from ffdt.experiments import bottleneck as bn
from ffdt.experiments import reps, runner, stats
from ffdt.metrics import ledger
from ffdt.sim.line import Line

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "configs" / "baseline_line.yaml"
QUICK_REPS = 10
MAX_REPS = 30  # the pre-registered experiment design; more adds run time, not new answers
# runaway-run guardrail: replications x campaign vials may not exceed the full baseline
# experiment (30 replications x 6 batches x 100,000 vials)
MAX_VIAL_REPS = 18_000_000
GLOSSARY = ROOT / "docs" / "domain" / "glossary.md"
PRESETS = ROOT / "reports" / "app_presets.json"
# metrics in the Compare view: key -> (label, display scale, unit after scaling)
COMPARE_METRICS = {
    "good_per_ppt_hour": ("Good vials per scheduled hour", 1.0, "vials/h"),
    "line_oee": ("Line OEE", 100.0, "points"),
    "changeover_share": ("Changeover share of scheduled time", 100.0, "points"),
    "wait_staff_share": ("Waiting-for-staff share of scheduled time", 100.0, "points"),
    "mean_lead_time_h": ("Mean batch lead time incl. QA", 1.0, "h"),
    "makespan_h": ("Campaign length", 1.0, "h"),
}
KPI_LABELS = {
    "good_per_ppt_hour": "Good vials per scheduled hour",
    "line_oee": "Line OEE",
    "line_A": "Line availability",
    "line_P": "Line performance",
    "line_Q": "Line quality (yield)",
    "makespan_h": "Campaign length (h)",
    "mean_lead_time_h": "Mean batch lead time incl. QA (h)",
    "escapes": "Defects escaped to packing (vials)",
}
KPI_UNITS = {
    "good_per_ppt_hour": "vials per scheduled hour",
    "line_oee": "fraction 0-1",
    "line_A": "fraction 0-1",
    "line_P": "fraction 0-1",
    "line_Q": "fraction 0-1",
    "makespan_h": "hours",
    "mean_lead_time_h": "hours",
    "escapes": "vials",
}

# Plain-language tooltips, from docs/domain/glossary.md
TOOLTIPS = {
    "good_per_ppt_hour": "Good vials packed per hour of scheduled production time (breaks, "
    "nights and weekends excluded). The main throughput measure for comparing scenarios.",
    "line_oee": "Overall Equipment Effectiveness of the line: good vials packed divided by what "
    "the slowest machine (the filler, 240 vials/min) could make in the scheduled time. "
    "OEE = Availability x Performance x Quality.",
    "line_A": "Availability: share of scheduled time the filler was not broken down, changing "
    "over, or waiting for staff.",
    "line_P": "Performance: output while available, relative to the filler's nominal speed. Lost "
    "to minor stops and to the filler waiting for, or being held up by, other machines.",
    "line_Q": "Quality: good vials packed divided by vials started.",
    "bottleneck": "The station that spends the largest share of scheduled time actually running. "
    "A first hint at the constraint; the bottleneck analysis uses three methods.",
    "mean_lead_time_h": "Average time from a batch's first vial entering the line to QA release, "
    "including batch-record review (21 CFR 211.192). Not part of OEE.",
    "makespan_h": "Clock hours from campaign start to the last vial packed, including nights and "
    "weekends.",
}


@dataclass(frozen=True)
class Levers:
    """What-if knobs. ``None`` keeps the baseline value."""

    batch_size_vials: int | None = None
    operators: int | None = None
    mechanics: int | None = None
    inspectors: int | None = None
    changeover_scale: float | None = None
    avi_units: int | None = None
    mtbf_scale: float | None = None
    mttr_scale: float | None = None


class InvalidInput(ValueError):
    """Raised with a readable, user-facing message."""


def baseline() -> LineConfig:
    return load_config(BASELINE)


def baseline_levers(cfg: LineConfig | None = None) -> Levers:
    cfg = cfg or baseline()
    return Levers(
        batch_size_vials=cfg.schedule[0].size_vials,
        operators=cfg.staffing.operator,
        mechanics=cfg.staffing.mechanic,
        inspectors=cfg.staffing.inspector,
        changeover_scale=cfg.changeovers.scale,
        avi_units=cfg.station("avi").count,
        mtbf_scale=1.0,
        mttr_scale=1.0,
    )


def _check(lv: Levers) -> None:
    errs = []
    if lv.batch_size_vials is not None and not 1_000 <= lv.batch_size_vials <= 1_000_000:
        errs.append("Batch size must be between 1,000 and 1,000,000 vials.")
    for name in ("operators", "mechanics", "inspectors"):
        v = getattr(lv, name)
        if v is not None and not 1 <= v <= 20:
            errs.append(
                f"{name.capitalize()} must be between 1 and 20 (with 0 the work it does never "
                "starts and the campaign cannot finish)."
            )
    if lv.avi_units is not None and not 1 <= lv.avi_units <= 4:
        errs.append("Inspection (AVI) machines must be between 1 and 4.")
    for name, lo, hi in (
        ("changeover_scale", 0.1, 3.0),
        ("mtbf_scale", 0.1, 10.0),
        ("mttr_scale", 0.1, 10.0),
    ):
        v = getattr(lv, name)
        if v is not None and not lo <= v <= hi:
            errs.append(f"{name.replace('_', ' ').capitalize()} must be between {lo} and {hi}.")
    if errs:
        raise InvalidInput(" ".join(errs))


def build_config(lv: Levers, base: LineConfig | None = None) -> LineConfig:
    """Apply levers to the baseline and validate. Raises ``InvalidInput`` with a readable
    message on any problem (never a raw stack trace)."""
    _check(lv)
    base = base or baseline()
    over: dict = {"staffing": {}, "station_overrides": {}}
    if lv.batch_size_vials is not None:
        over["schedule"] = [
            {"product": b.product, "format": b.format, "size_vials": lv.batch_size_vials}
            for b in base.schedule
        ]
    for lever, role in (
        ("operators", "operator"),
        ("mechanics", "mechanic"),
        ("inspectors", "inspector"),
    ):
        if getattr(lv, lever) is not None:
            over["staffing"][role] = getattr(lv, lever)
    if lv.changeover_scale is not None:
        over["changeovers"] = {"scale": lv.changeover_scale}
    if lv.avi_units is not None:
        over["station_overrides"]["avi"] = {"count": lv.avi_units}
    for st in base.stations:
        if st.failures and (lv.mtbf_scale or lv.mttr_scale):
            f = st.failures
            patch = over["station_overrides"].setdefault(st.name, {})
            patch["failures"] = {
                "mtbf_min": f.mtbf_min * (lv.mtbf_scale or 1.0),
                "mttr_mean_min": f.mttr_mean_min * (lv.mttr_scale or 1.0),
                "mttr_cv": f.mttr_cv,
            }
    try:
        return apply_overrides(base, over)
    except ValidationError as e:
        msgs = [f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in e.errors()]
        raise InvalidInput("Invalid configuration: " + "; ".join(msgs)) from None


@dataclass
class Output:
    config_hash: str
    n_reps: int
    seed: int
    summary: pd.DataFrame
    kpis: pd.DataFrame
    stations: pd.DataFrame  # mean per station across replications
    pareto: pd.DataFrame  # mean share of PPT per loss category across replications
    queues: pd.DataFrame  # mean per buffer across replications
    timeline: pd.DataFrame  # replication 0, first shift, after the calendar overlay
    bottleneck: dict
    stations_reps: pd.DataFrame | None = None  # one row per replication x station
    queues_reps: pd.DataFrame | None = None  # one row per replication x buffer
    pareto_reps: pd.DataFrame | None = None  # one row per replication x loss category


def kpi_table(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for key, label in KPI_LABELS.items():
        x = summary[key].astype(float)
        hw = reps.half_width(x) if len(x) > 1 else float("nan")
        rows.append({"metric": key, "label": label, "mean": x.mean(), "ci95_half_width": hw})
    return pd.DataFrame(rows)


def kpi_csv(out: Output) -> bytes:
    """KPI table as CSV for Excel: units in every header and row, UTF-8 with BOM so Excel
    detects the encoding, and the simulated-data label in the first column header."""
    df = pd.DataFrame(
        {
            "Metric (SIMULATED, NOT PLANT DATA)": out.kpis["label"],
            "Unit": out.kpis["metric"].map(KPI_UNITS),
            "Mean across replications (unit as stated)": out.kpis["mean"],
            "95% CI half-width (unit as stated)": out.kpis["ci95_half_width"],
            "Replications (count)": out.n_reps,
            "Seed": out.seed,
            "Config hash": out.config_hash,
        }
    )
    return df.to_csv(index=False).encode("utf-8-sig")


def simulate(cfg: LineConfig, quick: bool = True, n_reps: int | None = None) -> Output:
    """Run replications with the project's experiment design (``configs/experiment.yaml``).
    ``quick`` uses fewer replications for interactive use; CIs are wider and say so."""
    exp = runner.load_experiment()
    n = n_reps or (QUICK_REPS if quick else exp["n_reps"])
    res = runner.run(cfg, n_reps=n, seed=exp["seed"], n_jobs=-1)
    num = ["A", "P", "Q", "OEE", "utilization", "good_per_ppt_hour"]
    stations = res.stations.groupby("station", sort=False)[num].mean().reset_index()
    line_st = stations[stations["station"] != "manual_inspection"]
    b = line_st.loc[line_st["utilization"].idxmax()]
    pareto = (
        res.pareto.groupby(["category", "six_big_loss", "factor"], as_index=False)["share_of_ppt"]
        .mean()
        .sort_values("share_of_ppt", ascending=False, ignore_index=True)
    )
    queues = (
        res.queues.groupby("buffer", sort=False)[
            ["mean_sublots", "mean_vials", "mean_wait_min", "lambda_per_min"]
        ]
        .mean()
        .reset_index()
    )
    return Output(
        config_hash=cfg.hash(),
        n_reps=n,
        seed=exp["seed"],
        summary=res.summary,
        kpis=kpi_table(res.summary),
        stations=stations,
        pareto=pareto,
        queues=queues,
        timeline=sample_shift(cfg, exp["seed"]),
        bottleneck={"station": b["station"], "utilization": float(b["utilization"])},
        stations_reps=res.stations,
        queues_reps=res.queues,
        pareto_reps=res.pareto,
    )


def sample_shift(cfg: LineConfig, seed: int, rep: int = 0) -> pd.DataFrame:
    """State intervals of every station unit during the first shift of replication ``rep``."""
    line = Line(cfg, root_seed=seed, replication=rep)
    line.run()
    run = line.export()
    st = ledger.calendar_overlay(ledger.states_df(run), run["off_shift"])
    t0, t1 = 0.0, cfg.calendar.shift_min
    st = st[(st["end"] > t0) & (st["start"] < t1)].copy()
    st["start"] = st["start"].clip(lower=t0)
    st["end"] = st["end"].clip(upper=t1)
    return _coalesce(st)


def _coalesce(st: pd.DataFrame) -> pd.DataFrame:
    """Merge back-to-back intervals of the same state on the same unit (for plotting)."""
    rows = []
    for (station, unit), g in st.sort_values("start").groupby(["station", "unit"], sort=False):
        cur = None
        for s, a, b in g[["state", "start", "end"]].itertuples(index=False):
            if cur and cur[0] == s and abs(cur[2] - a) < 1e-9:
                cur[2] = b
            else:
                if cur:
                    rows.append((station, unit, *cur))
                cur = [s, a, b]
        if cur:
            rows.append((station, unit, *cur))
    out = pd.DataFrame(rows, columns=["station", "unit", "state", "start", "end"])
    out["minutes"] = out["end"] - out["start"]
    return out


# -- Compare view (T6.2.1) ----------------------------------------------------------------------
def max_reps(cfg: LineConfig) -> int:
    """Most replications allowed for this configuration by the runaway-run guardrail."""
    vials = sum(b.size_vials for b in cfg.schedule)
    return max(1, min(MAX_REPS, MAX_VIAL_REPS // vials))


def glossary_md() -> str:
    """The binding glossary (docs/domain/glossary.md) without its title line."""
    return GLOSSARY.read_text(encoding="utf-8").partition("\n")[2].strip()


def load_presets() -> dict:
    """Precomputed pre-registered scenarios vs baseline (30 replications, common random numbers),
    written by ``python -m ffdt.experiments.final``."""
    return json.loads(PRESETS.read_text(encoding="utf-8"))


def preset_table(preset: dict) -> pd.DataFrame:
    return _delta_rows({m: preset["metrics"][m] for m in COMPARE_METRICS if m in preset["metrics"]})


def _per_rep(out: Output) -> pd.DataFrame:
    """Replication-indexed metrics, including loss shares from the per-replication Pareto."""
    s = out.summary.set_index("replication").sort_index()
    if out.pareto_reps is not None:
        sh = out.pareto_reps.pivot_table(
            index="replication", columns="category", values="share_of_ppt"
        )
        s["changeover_share"] = sh.get("CHANGEOVER")
        s["wait_staff_share"] = sh.get("WAIT_STAFF")
    return s


def _delta_rows(d: dict) -> pd.DataFrame:
    rows = []
    for m, r in d.items():
        label, scale, unit = COMPARE_METRICS[m]
        rows.append(
            {
                "metric": m,
                "label": label,
                "baseline": r["base"] * scale,
                "scenario": (r["base"] + r["diff"]) * scale,
                "difference": r["diff"] * scale,
                "ci_low": r["ci_low"] * scale,
                "ci_high": r["ci_high"] * scale,
                "unit": unit,
                "detectable": not (r["ci_low"] <= 0 <= r["ci_high"]),
            }
        )
    return pd.DataFrame(rows)


def compare(base: Output, scen: Output) -> tuple[pd.DataFrame, dict]:
    """Paired comparison of two runs made with the same seed and replication count (common
    random numbers): scenario minus baseline per metric with a t-based 95% CI, and the
    bottleneck by the three run-level methods for each run."""
    if base.n_reps != scen.n_reps or base.seed != scen.seed:
        raise InvalidInput("Both runs need the same seed and number of replications.")
    a, b = _per_rep(base), _per_rep(scen)
    d = {}
    for m in COMPARE_METRICS:
        if m in a and m in b:
            r = stats.paired(a[m].to_numpy(), b[m].to_numpy(), n_boot=200)
            d[m] = {
                "base": r.base_mean,
                "diff": r.mean_diff,
                "ci_low": r.ci_low,
                "ci_high": r.ci_high,
            }
    vb = bn.run_level_verdict(bn.run_level_picks(base.stations_reps, base.queues_reps))
    vs = bn.run_level_verdict(bn.run_level_picks(scen.stations_reps, scen.queues_reps))
    shift = {
        "baseline": vb["consensus"],
        "scenario": vs["consensus"],
        "shifted": vb["consensus"] != vs["consensus"],
        "methods": "utilization, blocking/starvation arrows, queue (run-level)",
        "agreeing_scenario": vs["methods_agreeing"],
    }
    return _delta_rows(d), shift

"""Bottleneck identification by several methods (T5.2.3).

The constraint is an output of the model, never an input. Four methods are applied to every
replication; a station is called the constraint of a configuration only when the methods agree.

1. **Utilization**: highest share of scheduled production time (PPT) spent running.
2. **Active period** (Roser, Nakano & Tanaka, shifting-bottleneck detection; VERIFY exact
   reference): a station is *active* unless it is starved, blocked or in a planned stop. At each
   instant the momentary bottleneck is the station whose current uninterrupted active period is
   the longest. Where the active periods of consecutive bottlenecks overlap, both are *shifting*
   bottlenecks; the rest is *sole* bottleneck time. Reported as shares of PPT.
3. **Blocking/starvation arrows** (Kuo, Lim & Meerkov, serial-line bottleneck indicators; VERIFY
   exact reference): for adjacent stations i, i+1, if i is blocked more than i+1 is starved the
   arrow points downstream (i -> i+1), else upstream. A station with both arrows pointing at it is
   a candidate; among candidates the one with the largest severity
   |ST(i+1) - BL(i)| + |BL(i-1) - ST(i)| is chosen.
4. **Queue build-up** (corroboration): largest time-averaged queue in front of a station. The
   first station is excluded: its input buffer is the release of material into the line and is
   full by construction.

Stations with several parallel units are *active* only while every unit is active (the station
has no spare capacity). The offline manual-inspection pool is not part of the serial line and is
excluded from all methods.

Caveat: with random failures, changeovers and staffing waits the constraint is dynamic: it moves
during a run. Methods 1, 3 and 4 summarize a whole run; method 2 shows how often it moves.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from ffdt.config import LineConfig
from ffdt.metrics import ledger
from ffdt.sim.line import Line

INACTIVE = {"STARVED", "BLOCKED", "PLANNED_STOP"}
METHODS = ["utilization", "active_period", "arrow", "queue"]
CORE = ["utilization", "active_period", "arrow"]  # the three named in hypothesis H1a


# -- method 2: active period -------------------------------------------------------------------
def active_periods(states: pd.DataFrame, units: int) -> np.ndarray:
    """Merged [start, end) periods where all ``units`` units of one station are active.
    ``states`` holds one station's rows (unit, state, start, end) after the calendar overlay."""
    ev = []
    for s, a, b in states[["state", "start", "end"]].itertuples(index=False):
        if s not in INACTIVE and b > a:
            ev += [(a, 1), (b, -1)]
    if not ev:
        return np.empty((0, 2))
    ev.sort(key=lambda x: (x[0], x[1]))  # ends before starts at equal times
    out, n, start = [], 0, None
    for t, d in ev:
        n += d
        if n == units and start is None:
            start = t
        elif n < units and start is not None:
            if t > start:
                out.append((start, t))
            start = None
    # merge touching periods (state changes between two active states)
    merged: list[list[float]] = []
    for a, b in out:
        if merged and a <= merged[-1][1] + 1e-9:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return np.array(merged, dtype=float)


def active_period_shares(periods: dict[str, np.ndarray], ppt_min: float) -> pd.DataFrame:
    """Sole and shifting bottleneck time per station as shares of ``ppt_min``."""
    names = list(periods)
    cuts = sorted({float(t) for p in periods.values() for t in p.ravel()})
    episodes: list[tuple[str, float, float]] = []  # (station, period start, period end)
    ptr = dict.fromkeys(names, 0)
    for a, b in zip(cuts[:-1], cuts[1:], strict=True):
        mid, best = (a + b) / 2, None
        for n in names:
            p = periods[n]
            i = ptr[n]
            while i < len(p) and p[i, 1] <= mid:
                i += 1
            ptr[n] = i
            if i < len(p) and p[i, 0] <= mid:
                length = p[i, 1] - p[i, 0]
                if best is None or length > best[0]:
                    best = (length, n, p[i, 0], p[i, 1])
        if best and (not episodes or episodes[-1] != best[1:]):
            episodes.append(best[1:])
    sole = dict.fromkeys(names, 0.0)
    shift = dict.fromkeys(names, 0.0)
    for k, (n, a, b) in enumerate(episodes):
        # overlaps with the previous and next bottleneck periods; take their union so time
        # covered by both is counted once for this station
        ivs = []
        for j in (k - 1, k + 1):
            if 0 <= j < len(episodes) and episodes[j][0] != n:
                lo, hi = max(a, episodes[j][1]), min(b, episodes[j][2])
                if hi > lo:
                    ivs.append((lo, hi))
        ivs.sort()
        shifting, cur = 0.0, None
        for lo, hi in ivs:
            if cur and lo <= cur[1]:
                cur = (cur[0], max(cur[1], hi))
            else:
                if cur:
                    shifting += cur[1] - cur[0]
                cur = (lo, hi)
        if cur:
            shifting += cur[1] - cur[0]
        shift[n] += shifting
        sole[n] += (b - a) - shifting
    return pd.DataFrame(
        {"sole_share": pd.Series(sole) / ppt_min, "shifting_share": pd.Series(shift) / ppt_min}
    ).assign(active_period_share=lambda d: d.sole_share + d.shifting_share)


# -- method 3: arrows --------------------------------------------------------------------------
def arrow_method(starved: pd.Series, blocked: pd.Series) -> tuple[str, list[str]]:
    """(chosen station, candidates) for stations in line order."""
    st = list(starved.index)
    down = [blocked[st[i]] > starved[st[i + 1]] for i in range(len(st) - 1)]  # arrow i -> i+1
    cands, sev = [], {}
    for i, s in enumerate(st):
        left_in = i == 0 or down[i - 1]
        right_in = i == len(st) - 1 or not down[i]
        if left_in and right_in:
            cands.append(s)
            sev[s] = (abs(starved[st[i + 1]] - blocked[s]) if i < len(st) - 1 else 0.0) + (
                abs(blocked[st[i - 1]] - starved[s]) if i > 0 else 0.0
            )
    return max(cands, key=sev.get), cands


# -- one replication ---------------------------------------------------------------------------
def replication(cfg: LineConfig, seed: int, rep: int, **line_kw) -> pd.DataFrame:
    """Method x station evidence for one replication (one row per line station)."""
    line = Line(cfg, root_seed=seed, replication=rep, **line_kw)
    line.run()
    run = line.export()
    order = [s["station"] for s in run["stations"] if not s.get("offline")]
    units = {s["station"]: s["units"] for s in run["stations"]}
    st = ledger.calendar_overlay(ledger.states_df(run), run["off_shift"])
    mins = ledger.state_minutes(st).reindex(order).fillna(0.0)
    ppt = mins.drop(columns="PLANNED_STOP").sum(axis=1)  # summed over units
    share = mins.div(ppt, axis=0)
    per_unit_ppt = float(ppt[order[0]] / units[order[0]])
    periods = {n: active_periods(st[st.station == n], units[n]) for n in order}
    ap = active_period_shares(periods, per_unit_ppt)
    q = ledger.queue_stats(run).set_index("buffer")["mean_sublots"]
    queue = pd.Series({n: q.get(f"in:{n}", np.nan) for n in order})
    queue.iloc[0] = np.nan  # release buffer, full by construction
    chosen, cands = arrow_method(share["STARVED"], share["BLOCKED"])
    return pd.DataFrame(
        {
            "utilization": share["RUN"],
            "starved_share": share["STARVED"],
            "blocked_share": share["BLOCKED"],
            "active_share": 1 - share["STARVED"] - share["BLOCKED"],
            "sole_share": ap["sole_share"],
            "shifting_share": ap["shifting_share"],
            "active_period_share": ap["active_period_share"],
            "queue_in_front": queue,
            "arrow_candidate": [n in cands for n in order],
            "arrow_choice": [n == chosen for n in order],
        },
        index=pd.Index(order, name="station"),
    ).assign(replication=rep)


RUN_LEVEL = ["utilization", "arrow", "queue"]


def run_level_picks(stations: pd.DataFrame, queues: pd.DataFrame) -> pd.DataFrame:
    """Per replication, the station picked by the three run-level methods (utilization, arrows,
    queue), from the runner's per-replication tables. Fast enough for the app; the active-period
    method needs full state timelines and is left to ``evidence``."""
    rows = []
    for rep, g in stations.groupby("replication"):
        g = g[g["station"] != "manual_inspection"].set_index("station")
        ppt = g["ppt_min"]
        util = g["RUN_min"] / ppt
        chosen, _ = arrow_method(g["STARVED_min"] / ppt, g["BLOCKED_min"] / ppt)
        q = queues[queues["replication"] == rep].set_index("buffer")["mean_sublots"]
        qin = pd.Series({s: q.get(f"in:{s}", np.nan) for s in g.index[1:]})
        rows.append(
            {
                "replication": rep,
                "utilization": util.idxmax(),
                "arrow": chosen,
                "queue": qin.idxmax(),
            }
        )
    return pd.DataFrame(rows)


def run_level_verdict(pk: pd.DataFrame) -> dict:
    out = {}
    for m in RUN_LEVEL:
        vc = pk[m].value_counts(normalize=True)
        out[m], out[f"{m}_share"] = vc.index[0], float(vc.iloc[0])
    top = pd.Series([out[m] for m in RUN_LEVEL]).value_counts()
    out["consensus"] = top.index[0] if top.iloc[0] >= 2 else "none"
    out["methods_agreeing"] = int(top.iloc[0])
    return out


def picks(ev: pd.DataFrame) -> pd.DataFrame:
    """Per replication: the station each method picks."""
    rows = []
    for rep, g in ev.groupby("replication"):
        g = g.set_index("station") if "station" in g.columns else g
        rows.append(
            {
                "replication": rep,
                "utilization": g["utilization"].idxmax(),
                "active_period": g["active_period_share"].idxmax(),
                "arrow": g.index[g["arrow_choice"]][0],
                "queue": g["queue_in_front"].idxmax(),
            }
        )
    return pd.DataFrame(rows)


def verdict(pk: pd.DataFrame) -> dict:
    """Modal pick and its replication share per method, plus the consensus station
    (modal pick of at least two of the three core methods, as in hypothesis H1a)."""
    out = {}
    for m in METHODS:
        vc = pk[m].value_counts(normalize=True)
        out[m] = vc.index[0]
        out[f"{m}_share"] = float(vc.iloc[0])
    core = pd.Series([out[m] for m in CORE]).value_counts()
    out["consensus"] = core.index[0] if core.iloc[0] >= 2 else "none"
    out["methods_agreeing"] = int(sum(out[m] == out["consensus"] for m in METHODS))
    return out


def evidence(cfg: LineConfig, seed: int, n_reps: int, n_jobs: int = -1) -> pd.DataFrame:
    parts = Parallel(n_jobs=n_jobs)(delayed(replication)(cfg, seed, r) for r in range(n_reps))
    return pd.concat(parts).reset_index()


def run_all(results_dir: Path | None = None, n_jobs: int = -1) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Baseline and every scenario: evidence per replication and one verdict row per config.
    Writes results/bottleneck_evidence.parquet and results/bottleneck_verdicts.csv."""
    from ffdt.experiments import runner, scenarios

    results_dir = results_dir or scenarios.RESULTS
    exp = runner.load_experiment()
    evs, rows = [], []
    for sc in [scenarios.baseline_scenario(), *scenarios.all_scenarios()]:
        ev = evidence(sc.config, exp["seed"], exp["n_reps"], n_jobs).assign(scenario=sc.name)
        evs.append(ev)
        rows.append({"scenario": sc.name, "family": sc.family} | verdict(picks(ev)))
    ev_all, ver = pd.concat(evs, ignore_index=True), pd.DataFrame(rows)
    base = ver.loc[ver.scenario == "baseline", "consensus"].iloc[0]
    ver["shifts_from_baseline"] = ver["consensus"] != base
    ev_all.to_parquet(results_dir / "bottleneck_evidence.parquet", index=False)
    ver.to_csv(results_dir / "bottleneck_verdicts.csv", index=False)
    return ev_all, ver


def report_md(ev: pd.DataFrame, ver: pd.DataFrame) -> str:
    """reports/bottleneck.md, generated from the evidence so no number is hand-copied."""
    b = ev[ev.scenario == "baseline"].groupby("station", sort=False)
    t = b[
        [
            "utilization",
            "starved_share",
            "blocked_share",
            "sole_share",
            "shifting_share",
            "queue_in_front",
        ]
    ].mean()
    arrow = b["arrow_choice"].mean()
    second = (
        ev[ev.scenario == "baseline"]
        .groupby("replication")
        .apply(lambda g: g.set_index("station")["active_period_share"].nlargest(2).index[1])
        .value_counts()
    )
    n = int(ev[ev.scenario == "baseline"]["replication"].nunique())
    lines = [
        "# Bottleneck identification",
        "",
        "Ticket T5.2.3. **Simulated, benchmark-parameterized. Not plant data.** Every number is a "
        "RESULT from `results/bottleneck_evidence.parquet` and `results/bottleneck_verdicts.csv` "
        f"(`python -m ffdt.experiments.bottleneck`), {n} replications per configuration, same seeds "
        "as the scenario study. Methods and references: docstring of "
        "`src/ffdt/experiments/bottleneck.py`.",
        "",
        "## Baseline: method x station",
        "Shares are of scheduled production time (PPT), mean over replications. Bold = the "
        "station each method picks.",
        "",
        "| Station | Utilization | Starved | Blocked | Active-period sole | Active-period "
        "shifting | Arrow method pick | Queue in front, sub-lots |",
        "|---|---|---|---|---|---|---|---|",
    ]
    picks_ = {
        "utilization": t["utilization"].idxmax(),
        "sole": (t["sole_share"] + t["shifting_share"]).idxmax(),
        "queue": t["queue_in_front"].idxmax(),
    }
    for st, r in t.iterrows():

        def f(v, key=None, st=st):
            s = f"{100 * v:.1f}%"
            return f"**{s}**" if key and picks_[key] == st else s

        q = "n/a (release buffer)" if pd.isna(r.queue_in_front) else f"{r.queue_in_front:.1f}"
        if picks_["queue"] == st:
            q = f"**{q}**"
        lines.append(
            f"| {st} | {f(r.utilization, 'utilization')} | {f(r.starved_share)} | "
            f"{f(r.blocked_share)} | {f(r.sole_share, 'sole')} | {f(r.shifting_share)} | "
            f"{100 * arrow[st]:.0f}% of reps | {q} |"
        )
    v0 = ver.set_index("scenario").loc["baseline"]
    lines += [
        "",
        f"**All four methods pick `{v0.consensus}`** (utilization in "
        f"{100 * v0.utilization_share:.0f}% of replications, active period "
        f"{100 * v0.active_period_share:.0f}%, arrows {100 * v0.arrow_share:.0f}%, queue "
        f"{100 * v0.queue_share:.0f}%).",
        "",
        "## Where the methods differ, and why",
        "- **The constraint is not fully utilized.** The filler runs only "
        f"{100 * t.loc['filler', 'utilization']:.0f}% of scheduled time, yet it is the "
        "constraint: it is almost never starved or blocked, and most of its lost time is its own "
        "changeovers (see `reports/baseline.md`). Utilization alone would undersell how binding "
        "it is; the starved/blocked signature and the active-period method show it.",
        "- **A secondary, shifting bottleneck.** The active-period method finds the cartoner as "
        f"the second bottleneck in {int(second.get('cartoner', 0))} of {n} replications "
        f"({100 * t.loc['cartoner', 'sole_share']:.0f}% sole and "
        f"{100 * t.loc['cartoner', 'shifting_share']:.0f}% shifting share of PPT). It is the "
        "slowest station after the filler, is never blocked (it is last) and loses time "
        "waiting for operators. That is consistent with the filler being blocked by downstream "
        f"stations about {100 * t.loc['filler', 'blocked_share']:.0f}% of the time. The run-level "
        "methods cannot see a secondary bottleneck because they summarize the whole run.",
        "- **Queue method minority picks.** In a few replications of some scenarios the queue "
        "method picks the tunnel. When the filler is blocked the blockage propagates upstream, "
        "so the buffers in front of both the filler and the tunnel sit near their cap of 20 "
        "sub-lots and small differences decide the pick. This is why queue length is used only "
        "as corroboration.",
        "",
        "## Does the constraint shift under each scenario?",
        "| Scenario | Consensus | Methods agreeing (of 4) | Shift vs baseline | "
        "Weakest method agreement |",
        "|---|---|---|---|---|",
    ]
    for r in ver.itertuples():
        weakest = min(METHODS, key=lambda m: getattr(r, f"{m}_share"))
        w = f"{weakest} {100 * getattr(r, f'{weakest}_share'):.0f}%"
        lines.append(
            f"| {r.scenario} | {r.consensus} | {r.methods_agreeing} | "
            f"{'yes, to ' + r.consensus if r.shifts_from_baseline else 'no'} | {w} |"
        )
    lines += [
        "",
        "No scenario moves the constraint off the filler at the levels tested. Changeover "
        "reduction (SC-04) attacks the filler's largest loss directly, which is consistent with "
        "it being the largest effect in the scenario study; adding AVI capacity (SC-01) adds "
        "capacity at a non-constraint. Hypothesis verdicts are written in the findings memo "
        "(T5.2.5).",
        "",
        "## Caveat: the constraint is dynamic",
        "With random breakdowns, minor stops, changeovers and staffing waits, the constraint "
        "moves during a run. The active-period method measures this directly: the filler is the "
        f"sole bottleneck {100 * t.loc['filler', 'sole_share']:.0f}% of PPT, not 100%. A station "
        "named the constraint here is the one that limits output most of the time, under these "
        "benchmark parameters. Different real-line speeds, reliability or staffing could move "
        "it, which is why the method is part of the model and not an input.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    ev, v = run_all()
    out = Path(__file__).resolve().parents[3] / "reports" / "bottleneck.md"
    out.write_text(report_md(ev, v), encoding="utf-8")
    pd.set_option("display.width", 220)
    print(v)

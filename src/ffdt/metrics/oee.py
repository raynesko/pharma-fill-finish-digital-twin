"""OEE, utilization, loss Pareto and run summary (T3.2.5; definitions: docs/domain/glossary.md).

Station OEE (glossary section 2):
  PPT = all minutes except PLANNED_STOP
  Operating = PPT - DOWN - CHANGEOVER - WAIT_STAFF                     (D1, D2)
  A = Operating / PPT;  P = processed / (Operating x rate);  Q = good / processed
  OEE = A x P x Q = good / (PPT x rate);  utilization = RUN / PPT
Line OEE (D4): good vials packed / (PPT x rate) of the reference station (slowest nominal rate);
A_line = A of the reference station, Q_line = packed / started, P_line is the residual.

Imports nothing from ``ffdt.sim``.
"""

from __future__ import annotations

import pandas as pd

from ffdt.metrics import ledger as L

AVAILABILITY_LOSSES = ("DOWN", "CHANGEOVER", "WAIT_STAFF")
PERFORMANCE_LOSSES = ("MINOR_STOP", "STARVED", "BLOCKED")

# glossary section 4: model category -> six big loss (and OEE factor)
SIX_BIG_LOSSES = {
    "DOWN": ("Equipment failure", "Availability"),
    "CHANGEOVER": ("Setup and adjustment", "Availability"),
    "WAIT_STAFF": ("Setup and adjustment (staff resource, D2)", "Availability"),
    "MINOR_STOP": ("Idling and minor stoppages", "Performance"),
    "STARVED": ("Idling and minor stoppages (starved, D3)", "Performance"),
    "BLOCKED": ("Idling and minor stoppages (blocked, D3)", "Performance"),
    "fill_weight": ("Process defects", "Quality"),
    "avi_confirmed": ("Process defects", "Quality"),
}


def station_oee(minutes: dict, processed: float, good: float, rate_vpm: float) -> dict:
    """OEE components for one station from its state minutes (all units summed)."""
    m = {s: float(minutes.get(s, 0.0)) for s in L.STATES}
    ppt = sum(v for s, v in m.items() if s != "PLANNED_STOP")
    operating = ppt - sum(m[s] for s in AVAILABILITY_LOSSES)
    A = operating / ppt if ppt else 0.0
    P = processed / (operating * rate_vpm) if operating else 0.0
    Q = good / processed if processed else 0.0
    return {
        "ppt_min": ppt,
        "operating_min": operating,
        "A": A,
        "P": P,
        "Q": Q,
        "OEE": A * P * Q,
        "utilization": m["RUN"] / ppt if ppt else 0.0,
        "processed": processed,
        "good": good,
        "good_per_ppt_hour": good / ppt * 60 if ppt else 0.0,
        **{f"{s}_min": v for s, v in m.items()},
    }


def station_table(run: dict) -> pd.DataFrame:
    """Per-station OEE after the calendar overlay, one row per station. For the offline
    manual-inspection pool, "good" is the vials it returned to the flow."""
    st = L.calendar_overlay(L.states_df(run), run["off_shift"])
    mins = L.state_minutes(st)
    out = L.outputs_df(run)
    agg = out.groupby("station")[["vials_in", "vials_out"]].sum()
    rows = []
    for s in run["stations"]:
        name = s["station"]
        processed = float(agg.loc[name, "vials_in"]) if name in agg.index else 0.0
        good = float(agg.loc[name, "vials_out"]) if name in agg.index else 0.0
        m = mins.loc[name].to_dict() if name in mins.index else {}
        rows.append(
            {"station": name, "rate_vpm": s["rate_vpm"], "units": s["units"]}
            | station_oee(m, processed, good, s["rate_vpm"])
        )
    return pd.DataFrame(rows)


def reference_station(run: dict) -> dict:
    """Slowest nominal rate among line (not offline) stations; first one wins ties (D4)."""
    line = [s for s in run["stations"] if not s.get("offline")]
    return min(line, key=lambda s: s["rate_vpm"] * s["units"])


def line_oee(run: dict, stations: pd.DataFrame | None = None) -> dict:
    stations = station_table(run) if stations is None else stations
    ref = reference_station(run)
    r = stations.set_index("station").loc[ref["station"]]
    ideal = r["ppt_min"] * ref["rate_vpm"]  # ppt_min is already summed over units
    oee = run["packed"] / ideal if ideal else 0.0
    A = r["A"]
    Q = run["packed"] / run["started"] if run["started"] else 0.0
    P = oee / (A * Q) if A * Q else 0.0
    return {
        "reference_station": ref["station"],
        "definition": "good vials packed / (PPT x nominal rate of slowest station) (D4)",
        "A": float(A),
        "P": float(P),
        "Q": float(Q),
        "OEE": float(oee),
        "ppt_min": float(r["ppt_min"]),
    }


def loss_pareto(run: dict, stations: pd.DataFrame | None = None) -> pd.DataFrame:
    """Line losses as fractions of the reference station's PPT, largest first.

    Time losses are the reference station's state minutes / PPT; quality losses are scrapped
    vials converted to minutes at the reference rate. ``other`` is the residual so the shares
    sum to 1 - line OEE exactly (e.g. vials still in WIP when a run is cut off)."""
    stations = station_table(run) if stations is None else stations
    ref = reference_station(run)
    r = stations.set_index("station").loc[ref["station"]]
    ppt, rate = r["ppt_min"], ref["rate_vpm"]  # ppt summed over units
    rows = [(s, r[f"{s}_min"] / ppt) for s in (*AVAILABILITY_LOSSES, *PERFORMANCE_LOSSES)]
    rows += [(c, v / rate / ppt) for c, v in run["scrap_by_cause"].items()]
    oee = line_oee(run, stations)["OEE"]
    rows.append(("other", (1 - oee) - sum(v for _, v in rows)))
    df = pd.DataFrame(rows, columns=["category", "share_of_ppt"])
    df["six_big_loss"] = df["category"].map(lambda c: SIX_BIG_LOSSES.get(c, ("Other", "-"))[0])
    df["factor"] = df["category"].map(lambda c: SIX_BIG_LOSSES.get(c, ("Other", "-"))[1])
    return df.sort_values("share_of_ppt", ascending=False, ignore_index=True)


def summarize(run: dict) -> dict:
    """One flat row per replication: the primary and secondary scenario metrics."""
    stations = station_table(run)
    lo = line_oee(run, stations)
    b = L.batches_df(run)
    T = run["horizon_min"]
    return {
        "config_hash": run["config_hash"],
        "root_seed": run["root_seed"],
        "replication": run["replication"],
        "completed": run["completed"],
        "makespan_h": T / 60,
        "line_oee": lo["OEE"],
        "line_A": lo["A"],
        "line_P": lo["P"],
        "line_Q": lo["Q"],
        "good_vials": run["packed"],
        "good_per_ppt_hour": run["packed"] / lo["ppt_min"] * 60 if lo["ppt_min"] else 0.0,
        "good_per_calendar_hour": run["packed"] / T * 60 if T else 0.0,
        "yield": run["packed"] / run["started"] if run["started"] else 0.0,
        "escapes": run["escapes"],
        "mean_cycle_time_h": float(b["cycle_time_min"].mean() / 60),
        "mean_lead_time_h": float(b["lead_time_min"].mean() / 60),
        "mean_qa_queue_h": float(b["qa_queue_min"].mean() / 60),
        **L.wip_stats(run),
    }

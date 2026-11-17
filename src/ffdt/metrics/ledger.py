"""Tidy DataFrames from a run export (T3.2.5). Imports nothing from ``ffdt.sim``.

Input is the plain dict from ``Line.export()`` (schema: docs/metrics_schema.md).
"""

from __future__ import annotations

import bisect

import numpy as np
import pandas as pd

STATES = [
    "RUN",
    "STARVED",
    "BLOCKED",
    "DOWN",
    "MINOR_STOP",
    "CHANGEOVER",
    "PLANNED_STOP",
    "WAIT_STAFF",
]


def states_df(run: dict) -> pd.DataFrame:
    df = pd.DataFrame(run["states"], columns=["station", "unit", "state", "start", "end"])
    df["minutes"] = df["end"] - df["start"]
    return df


def calendar_overlay(states: pd.DataFrame, off_shift: list[tuple[float, float]]) -> pd.DataFrame:
    """Split every interval at shift boundaries; any off-shift part becomes PLANNED_STOP.

    The sim records PLANNED_STOP only for a unit that is mid-activity at shift end; a unit
    that is STARVED, BLOCKED or WAIT_STAFF across the night keeps that state. After the overlay
    every unit's PLANNED_STOP equals the off-shift minutes of the horizon (T3.2.5)."""
    if not off_shift:
        return states.copy()
    starts = [a for a, _ in off_shift]
    rows = []
    for st, u, s, a, b in states[["station", "unit", "state", "start", "end"]].itertuples(
        index=False
    ):
        t = a
        k = max(0, bisect.bisect_right(starts, a) - 1)
        while t < b:
            # next off window that ends after t
            while k < len(off_shift) and off_shift[k][1] <= t:
                k += 1
            if k == len(off_shift) or off_shift[k][0] >= b:
                rows.append((st, u, s, t, b))
                break
            o0, o1 = off_shift[k]
            if t < o0:
                rows.append((st, u, s, t, o0))
                t = o0
            seg_end = min(b, o1)
            rows.append((st, u, "PLANNED_STOP", t, seg_end))
            t = seg_end
    out = pd.DataFrame(rows, columns=["station", "unit", "state", "start", "end"])
    out = out[out["end"] > out["start"]].reset_index(drop=True)
    out["minutes"] = out["end"] - out["start"]
    return out


def state_minutes(states: pd.DataFrame) -> pd.DataFrame:
    """Minutes per station (summed over units) x state; all eight states as columns."""
    pv = states.pivot_table(
        index="station", columns="state", values="minutes", aggfunc="sum", fill_value=0.0
    )
    return pv.reindex(columns=STATES, fill_value=0.0)


def outputs_df(run: dict) -> pd.DataFrame:
    return pd.DataFrame(
        run["outputs"], columns=["station", "unit", "time", "batch_id", "vials_in", "vials_out"]
    )


def batches_df(run: dict) -> pd.DataFrame:
    df = pd.DataFrame(run["batches"])
    df["cycle_time_min"] = df["end_min"] - df["start_min"]
    df["lead_time_min"] = df["release_min"] - df["start_min"]
    df["yield"] = df["packed"] / df["size"]
    return df


def queue_stats(run: dict) -> pd.DataFrame:
    """Per buffer over [0, horizon]: time-weighted mean length L (sub-lots and vials), arrival
    rate lambda (sub-lots/min), mean time in queue W (min, from matched entry/exit times), and
    the Little's Law ratio L / (lambda W) (should be ~1 when the buffer starts and ends empty)."""
    T = run["horizon_min"]
    q = pd.DataFrame(run["queues"], columns=["buffer", "time", "delta", "uid", "vials"])
    rows = []
    for name, g in q.groupby("buffer", sort=False):
        g = g.sort_values("time", kind="stable")
        t = np.append(g["time"].to_numpy(), T)
        n = np.cumsum(g["delta"].to_numpy())
        v = np.cumsum((g["delta"] * g["vials"]).to_numpy())
        dt = np.diff(t)
        ins = g[g["delta"] > 0].set_index("uid")["time"]
        outs = g[g["delta"] < 0].set_index("uid")["time"]
        matched = outs.index.intersection(ins.index)
        w = (outs.loc[matched] - ins.loc[matched]).mean() if len(matched) else 0.0
        arrivals = len(ins)
        lam = arrivals / T if T > 0 else 0.0
        L = float(np.sum(n * dt) / T) if T > 0 else 0.0
        rows.append(
            {
                "buffer": name,
                "mean_sublots": L,
                "mean_vials": float(np.sum(v * dt) / T) if T > 0 else 0.0,
                "max_sublots": int(n.max()) if len(n) else 0,
                "arrivals": arrivals,
                "lambda_per_min": lam,
                "mean_wait_min": float(w),
                "littles_ratio": L / (lam * w) if lam * w > 0 else np.nan,
            }
        )
    return pd.DataFrame(rows)


def wip_stats(run: dict) -> dict:
    """Time-weighted mean and max WIP (vials started but not yet packed or scrapped)."""
    T = run["horizon_min"]
    f = pd.DataFrame(run["flow"], columns=["time", "kind", "batch_id", "vials"])
    if f.empty or T <= 0:
        return {"wip_mean_vials": 0.0, "wip_max_vials": 0}
    sign = f["kind"].map({"started": 1, "packed": -1, "scrapped": -1})
    f = f.assign(d=sign * f["vials"]).sort_values("time", kind="stable")
    t = np.append(f["time"].to_numpy(), T)
    w = np.cumsum(f["d"].to_numpy())
    return {
        "wip_mean_vials": float(np.sum(w * np.diff(t)) / T),
        "wip_max_vials": int(w.max()),
    }

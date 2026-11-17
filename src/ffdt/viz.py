"""Shared chart conventions and dashboard figures (dataviz method).

State colors use the validated 8-slot categorical palette in fixed order. Light mode passes all
checks; three slots (aqua, yellow, magenta) are below 3:1 contrast on the light surface, so every
state chart ships with a legend and a table view. Dark mode uses the same hues stepped for the
dark surface. Single-series charts use slot 1 only and carry no legend (the title names them).
Text is never drawn in a series color.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

STATE_ORDER = [
    "RUN",
    "STARVED",
    "BLOCKED",
    "DOWN",
    "MINOR_STOP",
    "CHANGEOVER",
    "PLANNED_STOP",
    "WAIT_STAFF",
]
STATE_COLORS = dict(
    zip(
        STATE_ORDER,
        ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"],
        strict=True,
    )
)
STATE_COLORS_DARK = dict(
    zip(
        STATE_ORDER,
        ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#0ca30c", "#9085e9", "#e66767"],
        strict=True,
    )
)
STATE_LABELS = {
    "RUN": "Running",
    "STARVED": "Starved (no input)",
    "BLOCKED": "Blocked (output full)",
    "DOWN": "Breakdown",
    "MINOR_STOP": "Minor stop",
    "CHANGEOVER": "Changeover",
    "PLANNED_STOP": "Planned stop (break)",
    "WAIT_STAFF": "Waiting for staff",
}
LOSS_LABELS = {
    "CHANGEOVER": "Changeover",
    "BLOCKED": "Filler blocked by downstream",
    "STARVED": "Filler starved by upstream",
    "MINOR_STOP": "Minor stops",
    "WAIT_STAFF": "Waiting for staff",
    "DOWN": "Breakdowns",
    "avi_confirmed": "Rejected defects (inspection)",
    "fill_weight": "Fill-weight rejects",
    "other": "Other / unexplained",
}
SIM_LABEL = "(simulated, benchmark-parameterized)"
SIM_TAG = "Simulated, benchmark-parameterized. Not plant data."


def series_color(dark: bool = False) -> str:
    return "#3987e5" if dark else "#2a78d6"


def _layout(fig: go.Figure, title: str, height: int) -> go.Figure:
    fig.update_layout(
        title=dict(text=f"{title}<br><sup>{SIM_TAG}</sup>", x=0, xanchor="left"),
        height=height,
        margin=dict(l=8, r=16, t=70, b=40),
        bargap=0.35,
        hoverlabel=dict(namelength=-1),
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, zeroline=False)
    fig.update_yaxes(showgrid=False, automargin=True)
    return fig


def pareto_fig(pareto: pd.DataFrame, dark: bool = False) -> go.Figure:
    """Line losses as % of scheduled production time at the filler, largest at the top.
    One series: single color, no legend, value labels on these few bars double as the table."""
    d = pareto[pareto["share_of_ppt"] > 1e-6].copy()
    d["label"] = d["category"].map(lambda c: LOSS_LABELS.get(c, c))
    d = d.sort_values("share_of_ppt")
    fig = go.Figure(
        go.Bar(
            x=d["share_of_ppt"] * 100,
            y=d["label"],
            orientation="h",
            marker=dict(color=series_color(dark), cornerradius=4, line=dict(width=0)),
            text=[f"{v:.1f}%" for v in d["share_of_ppt"] * 100],
            textposition="outside",
            cliponaxis=False,
            customdata=d[["six_big_loss", "factor"]].to_numpy(),
            hovertemplate="%{y}<br>%{x:.2f}% of scheduled time<br>"
            "Six big losses: %{customdata[0]} (%{customdata[1]})<extra></extra>",
            showlegend=False,
        )
    )
    top = float(d["share_of_ppt"].max() * 100) if len(d) else 1.0
    # headroom so the outside value label of the longest bar is never clipped (phone width)
    fig.update_xaxes(title="% of scheduled time (filler)", ticksuffix="%", range=[0, top * 1.25])
    return _layout(fig, "Where the time goes: loss Pareto", 360)


def majority_bins(tl: pd.DataFrame, bin_min: float = 5.0) -> pd.DataFrame:
    """Per station unit: the state with the most minutes in each ``bin_min`` bin, with runs of
    equal majority merged into one segment; ``mix`` gives every state's share in the segment
    (hover). Sub-minute RUN/STARVED/BLOCKED alternation otherwise renders as unreadable stripes."""
    t1 = tl["end"].max()
    edges = np.arange(0.0, t1 + bin_min, bin_min)
    rows = []
    for (station, unit), g in tl.groupby(["station", "unit"], sort=False):
        a, b, s = g["start"].to_numpy(), g["end"].to_numpy(), g["state"].to_numpy()
        seg = None  # [state, start, end, minutes-by-state]
        for lo, hi in zip(edges[:-1], edges[1:], strict=True):
            ov = np.clip(np.minimum(b, hi) - np.maximum(a, lo), 0, None)
            if ov.sum() <= 0:
                continue
            by = pd.Series(ov, index=s).groupby(level=0).sum()
            top = by.idxmax()
            if seg and seg[0] == top and abs(seg[2] - lo) < 1e-9:
                seg[2], seg[3] = hi, seg[3].add(by, fill_value=0)
            else:
                if seg:
                    rows.append(_segment(station, unit, seg))
                seg = [top, lo, hi, by]
        if seg:
            rows.append(_segment(station, unit, seg))
    return pd.DataFrame(rows)


def _segment(station, unit, seg) -> dict:
    state, lo, hi, by = seg
    share = (by / by.sum()).sort_values(ascending=False)
    mix = ", ".join(f"{STATE_LABELS[k]} {v:.0%}" for k, v in share.items() if v >= 0.05)
    return {
        "station": station,
        "unit": unit,
        "start": lo,
        "minutes": hi - lo,
        "state": state,
        "mix": mix,
    }


def timeline_fig(
    tl: pd.DataFrame, station_order: list[str], dark: bool = False, bin_min: float = 5.0
) -> go.Figure:
    """Station state timeline for one sample shift, majority state per ``bin_min`` bin. Legend
    always shown; the app provides the exact minutes as a table view."""
    colors = STATE_COLORS_DARK if dark else STATE_COLORS
    tl = majority_bins(tl, bin_min)
    multi = tl.groupby("station")["unit"].nunique()
    tl["row"] = [
        f"{s} #{u + 1}" if multi.get(s, 1) > 1 else s
        for s, u in zip(tl["station"], tl["unit"], strict=True)
    ]
    rows = []
    for s in station_order:
        rows += sorted(r for r in tl["row"].unique() if r == s or r.startswith(f"{s} #"))
    fig = go.Figure()
    for state in STATE_ORDER:
        d = tl[tl["state"] == state]
        if d.empty:
            continue
        fig.add_bar(
            y=d["row"],
            x=d["minutes"] / 60,
            base=d["start"] / 60,
            orientation="h",
            name=STATE_LABELS[state],
            marker=dict(color=colors[state], line=dict(width=0)),
            customdata=d[["mix"]].to_numpy(),
            hovertemplate="%{y}, %{base:.2f} h for %{x:.2f} h<br>%{customdata[0]}<extra></extra>",
        )
    fig.update_layout(barmode="overlay", legend=dict(orientation="h", y=-0.18, x=0, title=None))
    short = {r: r.replace("manual_inspection", "manual insp.") for r in rows}
    for tr in fig.data:
        tr.y = [short[r] for r in tr.y]
    fig.update_yaxes(categoryorder="array", categoryarray=[short[r] for r in reversed(rows)])
    fig.update_xaxes(title=f"Hours (main state per {bin_min:g} min)")
    return _layout(fig, "States in one sample shift", 440)


def queue_fig(queues: pd.DataFrame, dark: bool = False) -> go.Figure:
    """Mean time a sub-lot waits in each buffer (one series, line order top to bottom)."""
    d = queues.copy()
    d["label"] = d["buffer"].str.replace("in:", "before ", regex=False).str.replace("_", " ")
    d = d.iloc[::-1]
    fig = go.Figure(
        go.Bar(
            x=d["mean_wait_min"],
            y=d["label"],
            orientation="h",
            marker=dict(color=series_color(dark), cornerradius=4, line=dict(width=0)),
            customdata=d[["mean_sublots", "lambda_per_min"]].to_numpy(),
            hovertemplate="%{y}<br>mean wait %{x:.1f} min<br>mean queue %{customdata[0]:.1f}"
            " sub-lots<br>arrivals %{customdata[1]:.2f} per min<extra></extra>",
            showlegend=False,
        )
    )
    fig.update_xaxes(title="Mean wait per sub-lot (min)")
    return _layout(fig, "Queue time before each station", 340)

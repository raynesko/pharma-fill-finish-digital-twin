"""What-if app for the fill-finish line (T6.1.1 skeleton). Run: python tasks.py app

All model logic lives in ``ffdt``; this file only collects inputs and shows outputs via
``ffdt.api``.
"""

import time

import streamlit as st

from ffdt import api, viz

st.set_page_config(page_title="Fill-Finish Line What-If", layout="wide")


@st.cache_data(show_spinner=False, max_entries=32)
def run_cached(config_json: str, config_hash: str, quick: bool) -> api.Output:
    """Cached by config content (hash) and mode: identical inputs return instantly."""
    cfg = api.LineConfig.model_validate_json(config_json)
    return api.simulate(cfg, quick=quick)


base = api.baseline_levers()

st.title("Fill-finish line what-if")
st.caption(
    "SIMULATED, BENCHMARK-PARAMETERIZED LINE. NOT PLANT DATA. "
    "Baseline v1.0 (frozen): parameters are public-benchmark and engineering-judgment values "
    "(see docs/assumptions.md)."
)

with st.sidebar:
    st.header("Levers")
    with st.form("levers"):
        batch = st.number_input(
            "Batch size (vials)",
            min_value=1_000,
            max_value=1_000_000,
            value=base.batch_size_vials,
            step=10_000,
            help="Every batch in the 6-batch campaign gets this size.",
        )
        st.subheader("Staffing per shift")
        ops = st.number_input("Line operators (changeovers)", 1, 20, base.operators)
        mech = st.number_input("Mechanics (repairs)", 1, 20, base.mechanics)
        insp = st.number_input("Inspectors (manual re-inspection)", 1, 20, base.inspectors)
        st.subheader("Equipment")
        avi = st.number_input("Inspection (AVI) machines", 1, 4, base.avi_units)
        co = st.slider(
            "Changeover time (x baseline)",
            0.1,
            3.0,
            float(base.changeover_scale),
            0.05,
            help="0.5 = every changeover takes half as long (an assumption, not a measured "
            "SMED result).",
        )
        mtbf = st.slider("Time between breakdowns (x baseline)", 0.1, 10.0, 1.0, 0.1)
        mttr = st.slider("Repair time (x baseline)", 0.1, 10.0, 1.0, 0.1)
        quick = st.toggle(
            f"Quick mode ({api.QUICK_REPS} replications)",
            value=True,
            help="Off: the full experiment design (30 replications, narrower confidence intervals).",
        )
        submitted = st.form_submit_button("Run", type="primary", use_container_width=True)

levers = api.Levers(
    batch_size_vials=int(batch),
    operators=int(ops),
    mechanics=int(mech),
    inspectors=int(insp),
    changeover_scale=float(co),
    avi_units=int(avi),
    mtbf_scale=float(mtbf),
    mttr_scale=float(mttr),
)

try:
    cfg = api.build_config(levers)
except api.InvalidInput as e:
    st.error(str(e))
    st.stop()

if submitted:
    t0 = time.perf_counter()
    with st.spinner("Simulating..."):
        st.session_state["result"] = run_cached(cfg.model_dump_json(), cfg.hash(), quick)
    st.session_state["elapsed"] = time.perf_counter() - t0

out = st.session_state.get("result")
if out is None:
    st.info("Set the levers in the sidebar and press **Run**. The baseline is preloaded.")
    st.stop()

dark = getattr(getattr(st.context, "theme", None), "type", "light") == "dark"


def png_config(name: str) -> dict:
    """Plotly's toolbar camera button saves a PNG in the browser (no server-side renderer)."""
    return {
        "displaylogo": False,
        "toImageButtonOptions": {
            "format": "png",
            "filename": f"ffdt_{name}_{out.config_hash}",
            "scale": 2,
        },
    }


st.caption(
    f"Config {out.config_hash} · {out.n_reps} replications · seed {out.seed} · "
    f"{st.session_state.get('elapsed', 0):.1f} s · {viz.SIM_TAG}"
)

# -- KPI tiles: mean across replications, 95% CI half-width below ------------------------
k = out.kpis.set_index("metric")
tiles = [
    ("good_per_ppt_hour", "{:,.0f}", "Good vials / scheduled hour"),
    ("line_oee", "{:.1%}", "Line OEE"),
    ("mean_lead_time_h", "{:.0f} h", "Mean batch lead time"),
]
cols = st.columns(4)
for col, (m, fmt, label) in zip(cols, tiles, strict=False):
    col.metric(label, fmt.format(k.loc[m, "mean"]), help=api.TOOLTIPS[m])
    col.caption(f"95% CI ± {fmt.format(k.loc[m, 'ci95_half_width'])}")
cols[3].metric(
    f"Busiest station: {out.bottleneck['station']}",
    f"{out.bottleneck['utilization']:.0%} running",
    help=api.TOOLTIPS["bottleneck"],
)
cols[3].caption("share of scheduled time")
a, p, q = (k.loc[m, "mean"] for m in ("line_A", "line_P", "line_Q"))
st.markdown(
    f"OEE = **Availability {a:.1%}** × **Performance {p:.1%}** × **Quality {q:.2%}**",
    help=" ".join(api.TOOLTIPS[m] for m in ("line_A", "line_P", "line_Q")),
)

# -- Charts ------------------------------------------------------------------------------
st.plotly_chart(
    viz.pareto_fig(out.pareto, dark), use_container_width=True, config=png_config("loss_pareto")
)
with st.expander("Loss table " + viz.SIM_LABEL):
    t = out.pareto.assign(
        loss=out.pareto["category"].map(lambda c: viz.LOSS_LABELS.get(c, c)),
        pct_of_scheduled_time=(out.pareto["share_of_ppt"] * 100).round(2),
    )
    st.dataframe(
        t[["loss", "pct_of_scheduled_time", "six_big_loss", "factor"]],
        hide_index=True,
        use_container_width=True,
    )

order = [*api.baseline().model_dump()["stations"], {"name": "manual_inspection"}]
st.plotly_chart(
    viz.timeline_fig(out.timeline, [s["name"] for s in order], dark),
    use_container_width=True,
    config=png_config("timeline"),
)
with st.expander("Timeline table: minutes per state in the sample shift " + viz.SIM_LABEL):
    tbl = out.timeline.pivot_table(
        index="station", columns="state", values="minutes", aggfunc="sum", fill_value=0
    ).round(1)
    st.dataframe(tbl, use_container_width=True)

st.plotly_chart(
    viz.queue_fig(out.queues, dark), use_container_width=True, config=png_config("queues")
)
with st.expander("Queue table " + viz.SIM_LABEL):
    st.dataframe(out.queues.round(3), hide_index=True, use_container_width=True)

st.subheader("All KPIs " + viz.SIM_LABEL)
st.download_button(
    "Download KPI table (CSV)",
    data=api.kpi_csv(out),
    file_name=f"ffdt_kpis_{out.config_hash}.csv",
    mime="text/csv",
)
st.caption("To save a chart as PNG, use the camera icon in the chart's top-right toolbar.")
st.dataframe(
    out.kpis[["label", "mean", "ci95_half_width"]], hide_index=True, use_container_width=True
)
st.dataframe(out.stations.round(3), hide_index=True, use_container_width=True)

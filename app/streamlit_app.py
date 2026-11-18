"""What-if app for the fill-finish line (T6.1.1 skeleton). Run: python tasks.py app

All model logic lives in ``ffdt``; this file only collects inputs and shows outputs via
``ffdt.api``.
"""

import time

import streamlit as st

from ffdt import api, viz

st.set_page_config(page_title="Fill-Finish Line What-If", layout="wide")


@st.cache_data(show_spinner=False, max_entries=32)
def run_cached(config_json: str, config_hash: str, n_reps: int) -> api.Output:
    """Cached by config content (hash) and replication count: identical inputs return instantly."""
    cfg = api.LineConfig.model_validate_json(config_json)
    return api.simulate(cfg, n_reps=n_reps)


base = api.baseline_levers()
presets = api.load_presets()
# one preset button per required lever: inspection capacity, batch size, staffing, changeover
PRESET_BUTTONS = {
    "Second inspection machine": "sc01_avi_plus1",
    "Halve batch size": "sc02_batch_x0p5",
    "One more line operator": "sc03_operator_plus1",
    "Changeovers 50% shorter": "sc04_changeover_m50",
}
COMPARE = "Compare with baseline"


def open_preset(scenario_id: str) -> None:
    st.session_state["view"] = COMPARE
    st.session_state["preset"] = presets["scenarios"][scenario_id]["plain_name"]


st.title("Fill-finish line what-if")
st.caption(
    "SIMULATED, BENCHMARK-PARAMETERIZED LINE. NOT PLANT DATA. "
    "Baseline v1.0 (frozen): parameters are public-benchmark and engineering-judgment values "
    "(see docs/assumptions.md)."
)

st.markdown("**Try a pre-registered scenario** (precomputed, 30 replications, opens instantly):")
for col, (label, sid) in zip(st.columns(4), PRESET_BUTTONS.items(), strict=True):
    col.button(
        label,
        key=f"preset_{sid}",
        on_click=open_preset,
        args=(sid,),
        use_container_width=True,
        help=presets["scenarios"][sid]["plain_name"],
    )

with st.expander("How to read this page"):
    st.markdown(
        """
- **What this is.** A computer model of a sterile vial filling and packaging line, run many
  times with random breakdowns, defects and repair times. Every number is **simulated** from
  public benchmarks and judgment, **not plant data**.
- **The question it answers.** If we change one thing (batch size, staff, an extra
  inspection machine, faster changeovers), how many more good vials per scheduled hour do we
  get, and which machine then limits the line (the **bottleneck**)?
- **Ranges, not single numbers.** Each result is an average over several runs. The "95% CI"
  under a number is the range the true average plausibly lies in. More replications give a
  narrower range.
- **Compare view.** Shows *scenario minus baseline*. If the range of the difference includes
  zero, the change is greyed and flagged **no detectable difference**: do not act on it.
- **Practical significance.** The study decided in advance that a change matters if it adds
  at least **3% good vials per scheduled hour** or **2 OEE points** (TARGET, pre-registered).
- **Start here.** Press a scenario button above, or set the levers in the sidebar and
  press **Run**.
"""
    )

with st.expander("Glossary: how every number is defined"):
    st.markdown(api.glossary_md())

with st.sidebar:
    view = st.radio(
        "View",
        ["Explore one run", COMPARE],
        key="view",
        help="Compare: pre-registered scenarios (30 replications, precomputed) or your own levers "
        "against the baseline with the same random numbers.",
    )
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
        reps_req = st.slider(
            "Replications",
            3,
            api.MAX_REPS,
            api.QUICK_REPS,
            help=f"How many times the week is simulated. {api.QUICK_REPS} takes seconds; "
            f"{api.MAX_REPS} matches the study design and gives narrower ranges. The maximum "
            f"is {api.MAX_REPS}: the range narrows only with the square root of the count, so "
            "more replications cost run time without changing conclusions.",
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

# runaway-run guardrail: big batches x many replications would run for many minutes
n_reps = min(int(reps_req), api.max_reps(cfg))
if n_reps < reps_req:
    st.sidebar.warning(
        f"Replications limited to {n_reps} for this batch size. A run may simulate at most "
        f"{api.MAX_VIAL_REPS / 1e6:.0f} million vials in total (replications x vials in the "
        "6-batch campaign), the size of the full baseline study, so it finishes in reasonable "
        "time."
    )


def show_comparison(table, shift: dict, n_reps: int, source: str) -> None:
    """Delta table with CIs, a no-detectable-difference warning, and the bottleneck shift."""
    st.caption(f"{source} · {n_reps} replications per side · {viz.SIM_TAG}")
    t = table.set_index("metric")
    g = t.loc["good_per_ppt_hour"]
    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Good vials per scheduled hour",
        f"{g.scenario:,.0f}",
        f"{g.difference:+,.0f} ({g.difference / g.baseline:+.1%}) vs baseline",
        delta_color="normal" if g.detectable else "off",  # grey when not detectable
        help=api.TOOLTIPS["good_per_ppt_hour"],
    )
    c1.caption(f"95% CI of the difference {g.ci_low:+,.0f} to {g.ci_high:+,.0f}")
    o = t.loc["line_oee"]
    c2.metric(
        "Line OEE",
        f"{o.scenario:.1f}%",
        f"{o.difference:+.1f} points",
        delta_color="normal" if o.detectable else "off",
    )
    c2.caption(f"95% CI {o.ci_low:+.1f} to {o.ci_high:+.1f} points")
    moved = shift["shifted"]
    c3.metric(
        "Bottleneck",
        shift["scenario"],
        help="Station picked by most bottleneck methods (" + shift["methods"] + ").",
    )
    c3.caption(f"moved from {shift['baseline']}" if moved else "same as baseline (no shift)")
    flat = table.loc[~table["detectable"], "label"].tolist()
    if flat:
        st.warning(
            "No detectable difference (the 95% CI includes zero) for: " + ", ".join(flat) + "."
        )
    if moved:
        st.warning(
            f"The bottleneck shifts from **{shift['baseline']}** to **{shift['scenario']}**."
        )
    else:
        st.info(f"The bottleneck stays at the **{shift['scenario']}**.")
    show = table.assign(
        **{
            "95% CI of difference": table.apply(
                lambda r: f"{r.ci_low:+,.2f} to {r.ci_high:+,.2f}", axis=1
            ),
            "Detectable?": table["detectable"].map({True: "yes", False: "no (CI includes 0)"}),
        }
    )[
        [
            "label",
            "unit",
            "baseline",
            "scenario",
            "difference",
            "95% CI of difference",
            "Detectable?",
        ]
    ].rename(
        columns={
            "label": "Metric",
            "unit": "Unit",
            "baseline": "Baseline",
            "scenario": "Scenario",
            "difference": "Difference",
        }
    )
    st.dataframe(show.round(2), hide_index=True, use_container_width=True)
    st.caption(
        "Scenario minus baseline, paired by replication (common random numbers): replication r "
        "of both sides sees the same breakdowns and defects, so the difference isolates the "
        "change. Shares are of the filler's scheduled production time."
    )


if view == COMPARE:
    st.subheader("Compare with baseline " + viz.SIM_LABEL)
    names = {v["plain_name"]: k for k, v in presets["scenarios"].items()}
    custom = "Custom: the levers in the sidebar"
    pick = st.selectbox("Scenario", [*names, custom], key="preset")
    if pick != custom:
        p = presets["scenarios"][names[pick]]
        shift = {
            "baseline": presets["baseline_bottleneck"],
            "scenario": p["bottleneck"],
            "shifted": p["bottleneck"] != presets["baseline_bottleneck"],
            "methods": "4 methods: utilization, active period, blocking/starvation arrows, queue",
        }
        label = "pre-registered, exploratory" if p["set"] == "exploratory" else "pre-registered"
        show_comparison(api.preset_table(p), shift, p["n_reps"], f"Precomputed {label} scenario")
        st.stop()
    if submitted:
        t0 = time.perf_counter()
        with st.spinner("Simulating baseline and your scenario with the same random numbers..."):
            bcfg = api.build_config(base)
            n_pair = min(n_reps, api.max_reps(bcfg))  # both sides need the same count
            b_out = run_cached(bcfg.model_dump_json(), bcfg.hash(), n_pair)
            s_out = run_cached(cfg.model_dump_json(), cfg.hash(), n_pair)
            st.session_state["compare"] = api.compare(b_out, s_out) + (s_out.n_reps,)
        st.session_state["elapsed"] = time.perf_counter() - t0
    res = st.session_state.get("compare")
    if res is None:
        st.info(
            "Set the levers in the sidebar and press **Run** to compare them with the baseline."
        )
        st.stop()
    table, shift, n = res
    show_comparison(
        table,
        shift,
        n,
        f"Custom run · bottleneck by 3 run-level methods · "
        f"{st.session_state.get('elapsed', 0):.1f} s",
    )
    st.stop()

if submitted:
    t0 = time.perf_counter()
    with st.spinner("Simulating..."):
        st.session_state["result"] = run_cached(cfg.model_dump_json(), cfg.hash(), n_reps)
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

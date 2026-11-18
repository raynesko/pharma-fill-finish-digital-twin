import ast
import dataclasses
from pathlib import Path

import pytest

from ffdt import api

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "app" / "streamlit_app.py"


def test_baseline_levers_reproduce_baseline_config():
    base = api.baseline()
    assert api.build_config(api.baseline_levers(base)).hash() == base.hash()
    assert api.build_config(api.Levers()).hash() == base.hash()


def test_levers_change_the_right_fields():
    cfg = api.build_config(
        api.Levers(
            batch_size_vials=50_000,
            operators=6,
            changeover_scale=0.5,
            avi_units=2,
            mtbf_scale=2.0,
            mttr_scale=0.5,
        )
    )
    assert all(b.size_vials == 50_000 for b in cfg.schedule)
    assert cfg.staffing.operator == 6 and cfg.changeovers.scale == 0.5
    assert cfg.station("avi").count == 2
    assert cfg.station("filler").failures.mtbf_min == 2 * 4800
    assert cfg.station("filler").failures.mttr_mean_min == 0.5 * 75


@pytest.mark.parametrize(
    "lv,text",
    [
        (api.Levers(operators=0), "Operators must be between 1 and 20"),
        (api.Levers(batch_size_vials=10), "Batch size"),
        (api.Levers(changeover_scale=0), "Changeover scale"),
        (api.Levers(avi_units=9), "AVI"),
    ],
)
def test_invalid_inputs_give_readable_messages(lv, text):
    with pytest.raises(api.InvalidInput, match=text):
        api.build_config(lv)


def test_kpi_table_has_ci():
    out = api.simulate(api.build_config(api.Levers(batch_size_vials=10_000)), n_reps=3)
    assert out.n_reps == 3 and len(out.summary) == 3
    assert {"mean", "ci95_half_width"} <= set(out.kpis.columns)
    assert out.kpis["ci95_half_width"].notna().all()


def test_app_contains_no_simulation_logic():
    """The app may import streamlit, the standard library, ffdt.api and ffdt.viz (presentation)."""
    tree = ast.parse(APP.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("ffdt"):
            assert node.module == "ffdt" and {a.name for a in node.names} <= {"api", "viz"}
        if isinstance(node, ast.Import):
            assert not any(a.name.startswith("ffdt.") for a in node.names)
    src = APP.read_text(encoding="utf-8")
    for forbidden in ("simpy", "Line(", "ffdt.sim", "ffdt.metrics"):
        assert forbidden not in src


def test_app_starts_without_error():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not at.exception
    assert any("NOT PLANT DATA" in c.value for c in at.caption)


@pytest.mark.slow
def test_app_run_and_cache():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP), default_timeout=120).run()
    _run_button(at).click().run()
    assert not at.exception
    assert at.metric and at.session_state["elapsed"] < 30  # quick mode target
    assert len(at.get("plotly_chart")) == 3  # pareto, timeline, queues
    assert all(
        "NOT PLANT DATA" in c.value.upper() or "simulated" in c.value.lower()
        for c in at.caption[:2]
    )
    _run_button(at).click().run()
    assert at.session_state["elapsed"] < 1  # second identical run from cache
    assert at.get("download_button")  # CSV export present


def test_dashboard_figures_build_for_baseline_and_custom_run():
    from ffdt import viz

    small = 10_000  # structure test: a short campaign is enough
    for lv in (
        api.Levers(batch_size_vials=small),
        api.Levers(batch_size_vials=small, avi_units=2, operators=2),
    ):
        out = api.simulate(api.build_config(lv), n_reps=2)
        order = [s.name for s in api.build_config(lv).stations] + ["manual_inspection"]
        figs = [
            viz.pareto_fig(out.pareto),
            viz.timeline_fig(out.timeline, order),
            viz.queue_fig(out.queues, dark=True),
        ]
        for f in figs:
            assert viz.SIM_TAG in f.layout.title.text
            assert f.data
        rows = set(figs[1].layout.yaxis.categoryarray)
        if lv.avi_units == 2:
            assert {"avi #1", "avi #2"} <= rows


def test_kpi_csv_has_units_and_opens_as_excel_csv():
    import io

    import pandas as pd

    out = api.simulate(api.build_config(api.Levers(batch_size_vials=10_000)), n_reps=2)
    raw = api.kpi_csv(out)
    assert raw.startswith(b"\xef\xbb\xbf")  # BOM: Excel detects UTF-8
    df = pd.read_csv(io.BytesIO(raw), encoding="utf-8-sig")
    assert "Unit" in df.columns and df["Unit"].notna().all()
    assert any("NOT PLANT DATA" in c for c in df.columns)
    assert len(df) == len(api.KPI_LABELS)


# -- Compare view (T6.2.1) ------------------------------------------------------------------
def test_presets_load_fast_and_cover_every_scenario():
    import time

    t0 = time.perf_counter()
    p = api.load_presets()
    tables = {k: api.preset_table(v) for k, v in p["scenarios"].items()}
    assert time.perf_counter() - t0 < 2.0  # target in T6.2.1
    assert len(tables) == 11 and p["baseline_bottleneck"] == "filler"
    t = tables["sc01_avi_plus1"].set_index("metric")
    assert not t.loc["good_per_ppt_hour", "detectable"]  # second AVI: CI includes zero
    assert tables["sc04_changeover_m50"].set_index("metric").loc["good_per_ppt_hour", "detectable"]


@pytest.fixture(scope="module")
def small_runs():
    base = api.simulate(api.baseline(), n_reps=3)
    smed = api.simulate(api.build_config(api.Levers(changeover_scale=0.5)), n_reps=3)
    return base, smed


def test_custom_compare_uses_common_random_numbers(small_runs):
    base, smed = small_runs
    same, shift = api.compare(base, base)
    assert (same["difference"] == 0).all() and not same["detectable"].any()
    assert not shift["shifted"] and shift["baseline"] == "filler"
    t, shift = api.compare(base, smed)
    g = t.set_index("metric").loc["good_per_ppt_hour"]
    assert g.detectable and g.difference > 0 and g.ci_low > 0
    assert not shift["shifted"]


def test_compare_rejects_unpaired_runs(small_runs):
    base, _ = small_runs
    other = api.simulate(api.baseline(), n_reps=2)
    with pytest.raises(api.InvalidInput):
        api.compare(base, other)


def test_app_compare_view_shows_preset_with_warning_and_bottleneck():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP), default_timeout=60).run()
    at.radio[0].set_value("Compare with baseline").run()
    at.selectbox[0].set_value("Add a second AVI machine").run()
    assert not at.exception
    assert any("No detectable difference" in w.value for w in at.warning)
    assert any("stays at the **filler**" in i.value for i in at.info)
    assert at.dataframe


@pytest.mark.slow
def test_app_compare_view_custom_run():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP), default_timeout=300).run()
    at.radio[0].set_value("Compare with baseline").run()
    at.selectbox[0].set_value("Custom: the levers in the sidebar").run()
    _run_button(at).click().run()  # levers at baseline: identical to the baseline
    assert not at.exception
    assert any("No detectable difference" in w.value for w in at.warning)
    assert any("stays at the **filler**" in i.value for i in at.info)


def _run_button(at):
    return next(b for b in at.button if b.label == "Run")


def test_four_preset_buttons_open_their_scenarios_in_compare_view():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP), default_timeout=60).run()
    presets = [b for b in at.button if b.key and b.key.startswith("preset_")]
    assert len(presets) == 4
    plain = api.load_presets()["scenarios"]
    for b in presets:
        sid = b.key.removeprefix("preset_")
        b.click().run()
        assert not at.exception
        assert at.radio[0].value == "Compare with baseline"
        assert at.selectbox[0].value == plain[sid]["plain_name"]
        assert at.dataframe
    # one per required lever: inspection capacity, batch size, staffing, changeover
    assert {k.split("_")[0] for k in (b.key.removeprefix("preset_") for b in presets)} == {
        "sc01",
        "sc02",
        "sc03",
        "sc04",
    }


def test_help_panels_present_and_glossary_is_the_binding_one():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP), default_timeout=60).run()
    labels = [e.label for e in at.expander]
    assert "How to read this page" in labels
    assert any(lbl.startswith("Glossary") for lbl in labels)
    md = " ".join(m.value for m in at.markdown)
    assert "Planned production time (PPT)" in md and "Line OEE" in md
    assert api.glossary_md() in md


def test_replication_guardrail():
    small = api.build_config(api.baseline_levers())
    assert api.max_reps(small) == api.MAX_REPS
    big = api.build_config(dataclasses.replace(api.baseline_levers(), batch_size_vials=1_000_000))
    assert api.max_reps(big) == 3  # 18 M vial-replications / 6 M campaign vials
    assert api.max_reps(big) * sum(b.size_vials for b in big.schedule) <= api.MAX_VIAL_REPS


def test_app_caps_replications_for_huge_batches():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP), default_timeout=60).run()
    at.radio[0].set_value("Compare with baseline").run()  # a preset is shown: Run won't simulate
    at.number_input[0].set_value(1_000_000)
    next(s for s in at.slider if s.label == "Replications").set_value(30)
    _run_button(at).click().run()
    assert not at.exception
    assert any("Replications limited to 3" in w.value for w in at.sidebar.warning)

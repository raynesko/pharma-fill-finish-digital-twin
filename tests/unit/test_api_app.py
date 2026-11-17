import ast
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
    at.button[0].click().run()
    assert not at.exception
    assert at.metric and at.session_state["elapsed"] < 30  # quick mode target
    assert len(at.get("plotly_chart")) == 3  # pareto, timeline, queues
    assert all(
        "NOT PLANT DATA" in c.value.upper() or "simulated" in c.value.lower()
        for c in at.caption[:2]
    )
    at.button[0].click().run()
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

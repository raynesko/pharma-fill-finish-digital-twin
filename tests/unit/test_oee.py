import ast
from pathlib import Path

import pytest

from ffdt.config import load_config
from ffdt.metrics import ledger as L
from ffdt.metrics import oee
from ffdt.sim.line import Line

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "configs" / "baseline_line.yaml"

# glossary worked example: one station, 200 vpm, one 480 min shift
EXAMPLE = {
    "DOWN": 30,
    "CHANGEOVER": 40,
    "WAIT_STAFF": 10,
    "MINOR_STOP": 5,
    "STARVED": 20,
    "BLOCKED": 15,
    "RUN": 360,
}


def _example_run():
    t, states = 0.0, []
    for s, m in EXAMPLE.items():
        states.append(("s", 0, s, t, t + m))
        t += m
    return {
        "config_hash": "x",
        "root_seed": 0,
        "replication": 0,
        "completed": True,
        "horizon_min": 480.0,
        "off_shift": [],
        "stations": [{"station": "s", "rate_vpm": 200, "units": 1}],
        "states": states,
        "outputs": [("s", 0, 480.0, 0, 72_000, 70_560)],
        "events": [],
        "queues": [],
        "flow": [],
        "batches": [],
        "started": 72_000,
        "packed": 70_560,
        "scrapped": 1_440,
        "scrap_by_cause": {"avi_confirmed": 1_440},
        "escapes": 0,
    }


def test_glossary_worked_example_exact():
    r = oee.station_oee(EXAMPLE, processed=72_000, good=70_560, rate_vpm=200)
    assert r["ppt_min"] == 480 and r["operating_min"] == 400
    assert r["A"] == pytest.approx(400 / 480, abs=1e-12)
    assert r["P"] == pytest.approx(0.90, abs=1e-12)
    assert r["Q"] == pytest.approx(0.98, abs=1e-12)
    assert r["OEE"] == pytest.approx(0.735, abs=1e-12)
    assert r["OEE"] == pytest.approx(70_560 / (480 * 200), abs=1e-12)
    assert r["utilization"] == pytest.approx(0.75)
    assert r["good_per_ppt_hour"] == pytest.approx(8_820)


def test_glossary_loss_pareto():
    run = _example_run()
    par = oee.loss_pareto(run).set_index("category")["share_of_ppt"]
    expected = {
        "CHANGEOVER": 40 / 480,
        "DOWN": 30 / 480,
        "STARVED": 20 / 480,
        "BLOCKED": 15 / 480,
        "WAIT_STAFF": 10 / 480,
        "MINOR_STOP": 5 / 480,
        "avi_confirmed": 0.015,
    }
    for k, v in expected.items():
        assert par[k] == pytest.approx(v, abs=1e-12)
    assert par["other"] == pytest.approx(0, abs=1e-12)
    assert par.sum() == pytest.approx(1 - 0.735, abs=1e-12)
    assert oee.line_oee(run)["OEE"] == pytest.approx(0.735)


def test_six_big_losses_cover_every_loss_category():
    for s in (*oee.AVAILABILITY_LOSSES, *oee.PERFORMANCE_LOSSES, "fill_weight", "avi_confirmed"):
        assert s in oee.SIX_BIG_LOSSES


@pytest.fixture(scope="module")
def run():
    line = Line(load_config(BASE), root_seed=1, replication=4)  # a weekend-spill replication
    assert line.run()
    return line.export()


def test_overlay_makes_planned_stop_equal_for_every_unit(run):
    raw = L.states_df(run)
    st = L.calendar_overlay(raw, run["off_shift"])
    off = sum(b - a for a, b in run["off_shift"])
    per_unit = st.groupby(["station", "unit"])
    planned = st[st["state"] == "PLANNED_STOP"].groupby(["station", "unit"])["minutes"].sum()
    assert len(planned) == per_unit.ngroups
    assert planned.to_numpy() == pytest.approx(off)
    # overlay keeps every unit's total time and covers [0, horizon]
    assert per_unit["minutes"].sum().to_numpy() == pytest.approx(run["horizon_min"])
    assert raw.groupby(["station", "unit"])["minutes"].sum().to_numpy() == pytest.approx(
        run["horizon_min"]
    )


def test_station_identities(run):
    t = oee.station_table(run)
    for r in t.itertuples():
        assert r.OEE == pytest.approx(r.good / (r.ppt_min * r.rate_vpm))  # PPT sums units
        assert 0 <= r.A <= 1 and 0 <= r.Q <= 1 and 0 <= r.P <= 1 + 1e-9
        assert r.ppt_min == pytest.approx(t["ppt_min"].iloc[0] * r.units / t["units"].iloc[0])


def test_line_oee_and_pareto_reconcile(run):
    lo = oee.line_oee(run)
    assert lo["reference_station"] == "filler"
    assert lo["A"] * lo["P"] * lo["Q"] == pytest.approx(lo["OEE"])
    assert 0 < lo["OEE"] < 1
    par = oee.loss_pareto(run)
    assert par["share_of_ppt"].sum() == pytest.approx(1 - lo["OEE"])
    # complete run: everything started went through the filler, so no unexplained residual
    assert abs(par.set_index("category").loc["other", "share_of_ppt"]) < 1e-6


def test_littles_law_holds_for_every_buffer(run):
    q = L.queue_stats(run)
    assert set(q["buffer"]) >= {"in:washer", "in:filler", "in:avi", "in:manual_inspection"}
    assert q["littles_ratio"].to_numpy() == pytest.approx(1.0, rel=1e-6)


def test_wip_and_summary(run):
    s = oee.summarize(run)
    assert s["wip_mean_vials"] > 0
    assert s["good_vials"] + sum(run["scrap_by_cause"].values()) == run["started"]
    assert s["mean_lead_time_h"] > s["mean_cycle_time_h"]
    assert s["good_per_ppt_hour"] > s["good_per_calendar_hour"]


def test_metrics_package_imports_nothing_from_sim():
    for f in (ROOT / "src" / "ffdt" / "metrics").glob("*.py"):
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("ffdt.sim"), f.name
            if isinstance(node, ast.Import):
                assert not any(a.name.startswith("ffdt.sim") for a in node.names), f.name

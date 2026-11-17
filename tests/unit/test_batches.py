from pathlib import Path

import pytest
from simhelpers import state_minutes

from ffdt.config import apply_overrides, load_config
from ffdt.sim.batches import CO, batch_table, changeover_type, generate_schedule
from ffdt.sim.line import Line

BASE = Path(__file__).resolve().parents[2] / "configs" / "baseline_line.yaml"
A2, A10, B2, B10 = ("a", "2r"), ("a", "10r"), ("b", "2r"), ("b", "10r")


@pytest.fixture(scope="module")
def cfg():
    return load_config(BASE)


# full predecessor/successor matrix: (prev, next) -> expected type per scope
MATRIX = [
    # prev, nxt,  full,               packaging,         glass
    (A2, A2, CO.SAME_PRODUCT, CO.SAME_PRODUCT, CO.NONE),
    (A2, A10, CO.FORMAT_CHANGE, CO.FORMAT_CHANGE, CO.FORMAT_CHANGE),
    (A2, B2, CO.PRODUCT_CHANGE, CO.SAME_PRODUCT, CO.NONE),
    (A2, B10, CO.PRODUCT_CHANGE, CO.FORMAT_CHANGE, CO.FORMAT_CHANGE),
    (A10, A2, CO.FORMAT_CHANGE, CO.FORMAT_CHANGE, CO.FORMAT_CHANGE),
    (B10, A10, CO.PRODUCT_CHANGE, CO.SAME_PRODUCT, CO.NONE),
    (B10, A2, CO.PRODUCT_CHANGE, CO.FORMAT_CHANGE, CO.FORMAT_CHANGE),
    (B2, B2, CO.SAME_PRODUCT, CO.SAME_PRODUCT, CO.NONE),
]


@pytest.mark.parametrize("prev,nxt,full,packaging,glass", MATRIX)
def test_changeover_type_matrix(prev, nxt, full, packaging, glass):
    assert changeover_type(prev, nxt, "full") is full
    assert changeover_type(prev, nxt, "packaging") is packaging
    assert changeover_type(prev, nxt, "glass") is glass
    assert changeover_type(prev, nxt, "none") is CO.NONE
    assert changeover_type(None, nxt, "full") is CO.NONE


def test_unknown_scope_rejected():
    with pytest.raises(ValueError):
        changeover_type(A2, A10, "bogus")


def test_seeded_schedule_is_reproducible_and_covers_mix():
    s1 = generate_schedule(["a", "b"], ["2r", "10r"], 40, 1000, root_seed=5)
    s2 = generate_schedule(["a", "b"], ["2r", "10r"], 40, 1000, root_seed=5)
    assert s1 == s2
    assert {(b.product, b.format) for b in s1} == {A2, A10, B2, B10}


def _det_line(cfg, **kw):
    return Line(cfg, use_calendar=False, stochastic=False, quality=False, **kw)


def test_fixed_sequence_changeovers_logged_on_affected_stations(cfg):
    line = _det_line(cfg)
    assert line.run()
    ev = [(st, d[1], d[2]) for _t, kind, st, d in line.log.events if kind == "changeover"]
    # baseline: a2 a2 a10 b10 b10 b2 -> transitions into batches 1..5
    by_station = {}
    for st, co, to in ev:
        by_station.setdefault(st, []).append((to, co))
    assert by_station["filler"] == [
        (1, "same_product"),
        (2, "format_change"),
        (3, "product_change"),
        (4, "same_product"),
        (5, "format_change"),
    ]
    assert by_station["washer"] == [(2, "format_change"), (5, "format_change")]
    assert by_station["cartoner"] == [
        (1, "same_product"),
        (2, "format_change"),
        (3, "same_product"),
        (4, "same_product"),
        (5, "format_change"),
    ]
    # deterministic mode uses modal durations: logged CHANGEOVER time = sum of modes
    co = cfg.changeovers
    want_filler = (
        2 * co.same_product.mode_min + 2 * co.format_change.mode_min + co.product_change.mode_min
    )
    assert state_minutes(line.log, "filler")["CHANGEOVER"] == pytest.approx(want_filler)
    assert state_minutes(line.log, "washer")["CHANGEOVER"] == pytest.approx(
        2 * co.format_change.mode_min
    )


def test_changeover_scale_halves_time(cfg):
    half = apply_overrides(cfg, {"changeovers": {"scale": 0.5}})
    a, b = _det_line(cfg), _det_line(half)
    a.run(), b.run()
    ca = state_minutes(a.log, "filler")["CHANGEOVER"]
    assert state_minutes(b.log, "filler")["CHANGEOVER"] == pytest.approx(ca / 2)


def test_parallel_unit_catches_up_on_changeover(cfg):
    two = apply_overrides(cfg, {"station_overrides": {"avi": {"count": 2}}})
    line = _det_line(two)
    assert line.run()
    units = {d[0] for _t, k, st, d in line.log.events if k == "changeover" and st == "avi"}
    assert units == {0, 1}


def test_total_started_equals_schedule_and_batch_table(cfg):
    line = Line(cfg, root_seed=3)
    assert line.run()
    assert line.ledger.started == sum(b.size_vials for b in cfg.schedule)
    df = batch_table(line.ledger)
    assert list(df.columns) == [
        "batch_id", "product", "format", "size", "start_min", "end_min", "packed", "scrapped",
        "yield", "qa_queue_min", "review_min", "release_min", "lead_time_min",
    ]  # fmt: skip
    assert len(df) == len(cfg.schedule)
    assert (df["packed"] + df["scrapped"] == df["size"]).all()
    assert (df["end_min"] > df["start_min"]).all()
    assert df["yield"].between(0.95, 1.0).all()
    assert (df["release_min"] >= df["end_min"] + cfg.qa.review_min_min).all()

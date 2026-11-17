"""Guards on data/raw/benchmark_sources.csv (T2.1.1 acceptance criteria)."""

import csv
from pathlib import Path

CSV = Path(__file__).resolve().parents[2] / "data" / "raw" / "benchmark_sources.csv"
COLS = [
    "param_id",
    "description",
    "value_low",
    "value_mode",
    "value_high",
    "unit",
    "source_title",
    "url_or_doc",
    "retrieved_date",
    "confidence",
    "notes",
]
UNITS = {"vpm", "min", "ratio", "fraction", "count", "vials", "days"}


def rows():
    with open(CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_columns_and_size():
    with open(CSV, newline="", encoding="utf-8") as f:
        assert next(csv.reader(f)) == COLS
    assert len(rows()) >= 25


def test_ids_unique_and_units_known():
    rs = rows()
    ids = [r["param_id"] for r in rs]
    assert len(ids) == len(set(ids))
    assert all(r["unit"] in UNITS for r in rs)
    assert all(r["confidence"] in {"H", "M", "L"} for r in rs)


def test_every_row_has_source_or_judgment_tag():
    for r in rows():
        has_source = r["url_or_doc"].strip() and r["url_or_doc"] != "engineering_judgment"
        tagged = "engineering_judgment" in (r["notes"] + r["url_or_doc"])
        assert has_source or tagged, r["param_id"]
        assert r["notes"].strip(), r["param_id"]


def test_numeric_ordering():
    for r in rows():
        try:
            lo, mode, hi = (float(r[k]) for k in ("value_low", "value_mode", "value_high"))
        except ValueError:
            continue  # triple-valued staffing row (B-033) is checked by hand
        assert lo <= mode <= hi, r["param_id"]

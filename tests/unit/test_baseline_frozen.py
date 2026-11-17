"""Baseline v1.0 is frozen (T4.2.1): editing it without a version bump must fail CI."""

import re
from pathlib import Path

from ffdt.config import load_config

ROOT = Path(__file__).resolve().parents[2]


def test_baseline_hash_matches_baseline_definition():
    cfg = load_config(ROOT / "configs" / "baseline_line.yaml")
    doc = (ROOT / "docs" / "baseline_definition.md").read_text(encoding="utf-8")
    recorded = re.search(r"config hash `([0-9a-f]{12})`", doc).group(1)
    assert cfg.version == "1.0"
    assert cfg.hash() == recorded, "baseline changed: bump to v1.1 and add a changelog row"

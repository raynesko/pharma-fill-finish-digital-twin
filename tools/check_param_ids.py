#!/usr/bin/env python3
"""Fail if any numeric value in a config YAML lacks a `# src: B-xxx` comment whose IDs exist in
data/raw/benchmark_sources.csv (no orphan parameters). Experiment-design numbers (replication
count, seed, CI target) are not benchmark parameters; they cite the ticket that chose them with
`# design: T4.1.3` (the ticket file must exist).

    python tools/check_param_ids.py [configs/baseline_line.yaml ...]   # default: configs/**/*.yaml
"""

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NUMBER = re.compile(r"(?<![\w.\-])-?\d+(\.\d+)?(?![\w.\-])")
SRC = re.compile(r"#\s*src:\s*(.+)$")
DESIGN = re.compile(r"#\s*design:\s*(T\d+\.\d+\.\d+)(?![\d.])")


def known_ids() -> set[str]:
    with open(ROOT / "data" / "raw" / "benchmark_sources.csv", newline="", encoding="utf-8") as f:
        return {r["param_id"] for r in csv.DictReader(f)}


def check(path: Path, ids: set[str]) -> list[str]:
    errs = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        code, _, comment = line.partition("#")
        code = re.sub(r'"[^"]*"', "", code)  # ignore quoted strings like version: "0.1"
        if not NUMBER.search(code):
            continue
        if comment and (d := DESIGN.search("#" + comment)):
            if not list((ROOT / "planning" / "tickets").rglob(f"{d.group(1)}_*.md")):
                errs.append(f"{path.name}:{n}: design ticket {d.group(1)} not found")
            continue
        m = SRC.search("#" + comment) if comment else None
        if not m:
            errs.append(f"{path.name}:{n}: numeric value without '# src:' -> {line.strip()}")
            continue
        for pid in m.group(1).split():
            if pid not in ids:
                errs.append(f"{path.name}:{n}: unknown param_id {pid}")
    return errs


def main(argv: list[str]) -> int:
    ids = known_ids()
    paths = [Path(p) for p in argv] or sorted((ROOT / "configs").rglob("*.yaml"))
    errs = [e for p in paths for e in check(p, ids)]
    for e in errs:
        print("ERROR:", e)
    print(f"checked {len(paths)} file(s): {'OK' if not errs else f'{len(errs)} error(s)'}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

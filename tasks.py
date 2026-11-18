#!/usr/bin/env python3
"""Cross-platform task runner (Windows has no make). Usage: python tasks.py <test|lint|fix|verify|scenarios|results|app|all>."""

import subprocess
import sys

PY = sys.executable
TASKS = {
    "test": [[PY, "-m", "pytest"]],
    "lint": [[PY, "-m", "ruff", "check", "."], [PY, "-m", "ruff", "format", "--check", "."]],
    "fix": [[PY, "-m", "ruff", "check", "--fix", "."], [PY, "-m", "ruff", "format", "."]],
    "index": [[PY, "tools/build_index.py"]],
    "verify": [[PY, "-m", "pytest", "-m", "slow"], [PY, "tools/verification_report.py"]],
    # filled in by later tickets:
    "scenarios": [[PY, "-m", "ffdt.experiments.scenarios"]],
    "app": [[PY, "-m", "streamlit", "run", "app/streamlit_app.py"]],
}
# full pipeline from an empty results/ folder to reports/results_final.json (about 10 min on
# 16 cores; sensitivity is most of it). Fixed seeds, so the numbers reproduce exactly.
TASKS["results"] = [
    [PY, "-m", f"ffdt.experiments.{m}"]
    for m in ("scenarios", "baseline_report", "stats", "bottleneck", "sensitivity", "final")
]
TASKS["all"] = TASKS["lint"] + TASKS["test"] + TASKS["results"]  # T7.1.3

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "test"
    if name not in TASKS:
        raise SystemExit(f"unknown task {name!r}; choose from {', '.join(TASKS)}")
    for cmd in TASKS[name]:
        rc = subprocess.call(cmd)
        if rc:
            raise SystemExit(rc)

#!/usr/bin/env python3
"""Cross-platform task runner (Windows has no make). Usage: python tasks.py <test|lint|fix|verify|scenarios|app|all>."""

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
TASKS["all"] = TASKS["lint"] + TASKS["test"]  # scenarios run separately (T5.1.2); T7.1.3

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "test"
    if name not in TASKS:
        raise SystemExit(f"unknown task {name!r}; choose from {', '.join(TASKS)}")
    for cmd in TASKS[name]:
        rc = subprocess.call(cmd)
        if rc:
            raise SystemExit(rc)

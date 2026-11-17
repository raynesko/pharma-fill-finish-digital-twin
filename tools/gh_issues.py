#!/usr/bin/env python3
"""Create GitHub issues from the backlog with the gh CLI. Dry run by default.

    python tools/gh_issues.py            # prints the gh commands
    python tools/gh_issues.py --apply    # runs them (needs `gh auth login` and a repo remote)

Creates labels (priority, sub-epic, type) and one issue per ticket/story. Add the issues to a
GitHub Project afterwards (Project > Add items), or use `gh project item-add`.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
items = json.loads((ROOT / "planning" / "backlog.json").read_text(encoding="utf-8"))
apply = "--apply" in sys.argv


def run(cmd):
    print(" ".join(f'"{c}"' if " " in c else c for c in cmd))
    if apply:
        subprocess.run(cmd, check=False)


for lab in ["P0", "P1", "P2", "Story", "Task", "Spike", "Bug"] + [f"SE{i}" for i in range(1, 8)]:
    run(["gh", "label", "create", lab, "--force"])
for m in items:
    body_file = ROOT / m["path"]
    body = body_file.read_text(encoding="utf-8").split("---", 2)[2].strip()
    labels = [m["type"], m["sub_epic"]] + ([m["priority"]] if m["priority"] else [])
    cmd = ["gh", "issue", "create", "--title", f"[{m['id']}] {m['title']}", "--body", body]
    for lab in labels:
        cmd += ["--label", lab]
    run(cmd)

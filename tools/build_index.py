#!/usr/bin/env python3
"""Rebuild planning indexes from the ticket files (the ticket .md files are the source of truth).

Usage:
    python tools/build_index.py            # regenerate backlog.csv/json, BOARD.md, 02_stories_and_tickets.md
    python tools/build_index.py --check    # validate only (deps exist, no cycles, hours add up); exit 1 on error

Stdlib only. Ticket frontmatter: `key: <json value>` lines between two `---` fences.
Valid status values: todo | in_progress | blocked | done | cut
"""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TICKETS = ROOT / "planning" / "tickets"
PLAN = ROOT / "planning"
STATUSES = {"todo", "in_progress", "blocked", "done", "cut"}
SE_NAMES = {
    "SE1": "Domain Research & Problem Framing",
    "SE2": "Parameterization, Data & Assumptions",
    "SE3": "Simulation Model Build",
    "SE4": "Verification, Validation & Baseline",
    "SE5": "Scenario & Bottleneck Study",
    "SE6": "Interface: Streamlit What-If App",
    "SE7": "Documentation & Portfolio Packaging",
}


def parse(path):
    text = path.read_text(encoding="utf-8")
    _, fm, body = text.split("---", 2)
    meta = {}
    for line in fm.strip().splitlines():
        k, v = line.split(":", 1)
        meta[k.strip()] = json.loads(v.strip())
    meta["body"] = body.strip()
    meta["path"] = str(path.relative_to(ROOT)).replace("\\", "/")
    return meta


def key(i):
    return [int(x) for x in i[1:].split(".")]


def load():
    items = [parse(p) for p in sorted(TICKETS.rglob("*.md"))]
    return sorted(items, key=lambda m: key(m["id"]))


def check(items):
    errs = []
    ids = {m["id"] for m in items}
    tickets = {m["id"]: m for m in items if m["id"].startswith("T")}
    for m in items:
        if m["status"] not in STATUSES:
            errs.append(f"{m['id']}: bad status {m['status']!r}")
        for d in m["depends_on"]:
            if d not in ids:
                errs.append(f"{m['id']}: unknown dependency {d}")
        if m["id"].startswith("T") and m["parent"] not in ids:
            errs.append(f"{m['id']}: unknown parent {m['parent']}")
    # cycle check
    state = {}

    def visit(n, stack):
        if state.get(n) == 2:
            return
        if state.get(n) == 1:
            errs.append("dependency cycle: " + " -> ".join(stack + [n]))
            return
        state[n] = 1
        for d in tickets[n]["depends_on"]:
            if d in tickets:
                visit(d, stack + [n])
        state[n] = 2

    for n in tickets:
        visit(n, [])
    # a done ticket must not depend on an unfinished ticket
    for m in tickets.values():
        if m["status"] == "done":
            for d in m["depends_on"]:
                if d in tickets and tickets[d]["status"] not in ("done", "cut"):
                    errs.append(f"{m['id']} is done but depends on unfinished {d}")
    # unchecked criteria on done tickets
    for m in tickets.values():
        if m["status"] == "done" and "- [ ]" in m["body"]:
            errs.append(f"{m['id']} is done but has unchecked acceptance criteria")
    return errs


def rollup(items):
    tickets = [m for m in items if m["id"].startswith("T")]
    by_story = defaultdict(list)
    for m in tickets:
        by_story[m["parent"]].append(m)
    return tickets, by_story


def write_outputs(items):
    tickets, by_story = rollup(items)
    # CSV for import (GitHub: see tools/gh_issues.py)
    with open(PLAN / "backlog.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "id",
                "type",
                "title",
                "sub_epic",
                "parent",
                "priority",
                "estimate_h",
                "size",
                "week",
                "status",
                "depends_on",
                "path",
            ]
        )
        for m in items:
            est = m["estimate_h"]
            if m["type"] == "Story":
                est = sum(c["estimate_h"] for c in by_story[m["id"]])
            w.writerow(
                [
                    m["id"],
                    m["type"],
                    m["title"],
                    m["sub_epic"],
                    m["parent"],
                    m["priority"],
                    est,
                    m["size"],
                    m["week"],
                    m["status"],
                    ";".join(m["depends_on"]),
                    m["path"],
                ]
            )
    (PLAN / "backlog.json").write_text(
        json.dumps([{k: v for k, v in m.items() if k != "body"} for m in items], indent=2),
        encoding="utf-8",
    )

    # Board
    done_h = sum(m["estimate_h"] for m in tickets if m["status"] == "done")
    total_h = sum(m["estimate_h"] for m in tickets)
    p0 = [m for m in tickets if m["priority"] == "P0"]
    L = [
        "# Status board (generated by tools/build_index.py; do not edit by hand)",
        "",
        f"Progress: {done_h:g} / {total_h:g} estimated hours done "
        f"({100 * done_h / total_h:.0f}%). P0: {sum(m['estimate_h'] for m in p0 if m['status'] == 'done'):g} / "
        f"{sum(m['estimate_h'] for m in p0):g} h.",
        "",
    ]
    ready = [
        m
        for m in tickets
        if m["status"] == "todo"
        and all(
            next((x for x in tickets if x["id"] == d), {"status": "done"})["status"]
            in ("done", "cut")
            for d in m["depends_on"]
        )
    ]
    L += ["## Ready now (dependencies satisfied), in priority then week order", ""]
    for m in sorted(ready, key=lambda m: (m["priority"], m["week"], key(m["id"])))[:8]:
        L.append(
            f"- **{m['id']}** {m['title']} ({m['priority']}, {m['estimate_h']} h, week {m['week']})"
        )
    L += ["", "## By week", "", "| Week | Tickets | Hours | P0 hours |", "|---|---|---|---|"]
    wk = defaultdict(list)
    for m in tickets:
        wk[m["week"]].append(m)
    for w_ in sorted(wk):
        ms = wk[w_]
        L.append(
            f"| {w_} | {', '.join(m['id'] for m in ms)} | {sum(m['estimate_h'] for m in ms):g} | "
            f"{sum(m['estimate_h'] for m in ms if m['priority'] == 'P0'):g} |"
        )
    L += ["", "## By sub-epic", ""]
    for se in sorted(SE_NAMES):
        ms = [m for m in tickets if m["sub_epic"] == se]
        n_done = sum(1 for m in ms if m["status"] == "done")
        L.append(
            f"- **{se} {SE_NAMES[se]}**: {n_done}/{len(ms)} tickets done, "
            f"{sum(m['estimate_h'] for m in ms):g} h"
        )
    L += [
        "",
        "## All tickets",
        "",
        "| ID | Title | P | h | Wk | Status | Depends on |",
        "|---|---|---|---|---|---|---|",
    ]
    for m in tickets:
        L.append(
            f"| {m['id']} | {m['title']} | {m['priority']} | {m['estimate_h']:g} | {m['week']} | "
            f"{m['status']} | {', '.join(m['depends_on']) or '-'} |"
        )
    (PLAN / "BOARD.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    # Consolidated doc in the required ticket format
    L = [
        "# Stories and tickets (generated from planning/tickets/; edit the ticket files, not this)",
        "",
    ]
    for se in sorted(SE_NAMES):
        L += [f"## {se} - {SE_NAMES[se]}", ""]
        for s in [m for m in items if m["type"] == "Story" and m["sub_epic"] == se]:
            L += [
                s["body"],
                "",
                f"_Story rollup: {sum(c['estimate_h'] for c in by_story[s['id']]):g} h_",
                "",
            ]
            for c in by_story[s["id"]]:
                L += [c["body"], ""]
            L += ["---", ""]
    (PLAN / "02_stories_and_tickets.md").write_text("\n".join(L), encoding="utf-8")


def main():
    items = load()
    errs = check(items)
    tickets = [m for m in items if m["id"].startswith("T")]
    total = sum(m["estimate_h"] for m in tickets)
    p0 = sum(m["estimate_h"] for m in tickets if m["priority"] == "P0")
    print(f"{len(items)} items, {len(tickets)} tickets, {total:g} h total, P0 {p0:g} h")
    for e in errs:
        print("ERROR:", e)
    if errs:
        sys.exit(1)
    if "--check" not in sys.argv:
        write_outputs(items)
        print("wrote backlog.csv, backlog.json, BOARD.md, 02_stories_and_tickets.md")


if __name__ == "__main__":
    main()

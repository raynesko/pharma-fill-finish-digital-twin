# Pharma Fill-Finish Digital Twin

*Status: planned, no code yet. The public README is written in ticket T7.1.1; this page is the working index.*

A discrete-event simulation of a sterile vial fill-finish line (washing, depyrogenation, filling, capping, inspection, labeling, packaging, QA release) to rank improvement levers and find the bottleneck, with a what-if web app. Simulated and benchmark-parameterized; no plant data.

## Where things are
| Need | Open |
|---|---|
| Scope, targets, risks | `planning/00_charter.md` |
| Epic, sub-epics, critical path | `planning/01_epic_breakdown.md` |
| All stories and tickets (consolidated) | `planning/02_stories_and_tickets.md` |
| Week plan, cut ladder | `planning/03_sprint_plan_and_cut_list.md` |
| Validation and the resume numbers | `planning/04_validation_and_metrics_plan.md` |
| Repo layout, naming, requirements | `planning/05_repo_structure.md` |
| Definition of Done | `planning/06_definition_of_done.md` |
| Bullets, pitch, slides, Q&A | `planning/07_portfolio_packaging.md` |
| Open questions with defaults | `planning/08_risks_and_open_questions.md` |
| Live status and next ticket | `planning/BOARD.md` |
| One file per ticket (agents) | `planning/tickets/` |
| Original brief | `planning/brief.md` |
| Agent rules | `CLAUDE.md` |

## Start
```
python tools/build_index.py        # refresh board
# then in Claude Code: /next-ticket
```
First ready tickets: T1.1.1, T1.1.2, T3.1.1.

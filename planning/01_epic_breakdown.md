# Epic breakdown

**EPIC-1: Pharma Fill-Finish Digital Twin** — a verified discrete-event simulation of an aseptic vial line with a pre-registered scenario study and a non-technical what-if app.

Hours below are ticket-estimate rollups (see `BOARD.md` for live numbers). Capacity: 8 weeks x about 9 h = 72 h. P0 total is 61.5 h, leaving about 10 h buffer; P1 and P2 are cut first.

| Sub-epic | Name | Build order rationale | Stories | Hours (P0 / all) | Exit criteria |
|---|---|---|---|---|---|
| SE1 | Domain Research & Problem Framing | Domain errors are the costliest to fix later | S1.1, S1.2 | 5.5 / 5.5 | Process map, glossary and pre-registered hypotheses committed |
| SE2 | Parameterization, Data & Assumptions | No code runs on invented numbers | S2.1 | 8 / 8 | Zero orphan config values; schema validates; distributions tested |
| SE3 | Simulation Model Build | Needs SE1 definitions and SE2 config | S3.1, S3.2 | 21.5 / 21.5 | Baseline week runs; all four scenario levers are config parameters |
| SE4 | Verification, Validation & Baseline | Gate before any scenario | S4.1, S4.2 | 7.5 / 9.5 | Tests green; baseline frozen at tag `baseline-v1.0`; baseline report done |
| SE5 | Scenario & Bottleneck Study | Core resume content | S5.1, S5.2 | 7.5 / 10.5 | `results_final.json` frozen; findings memo done |
| SE6 | Interface: Streamlit What-If App | Wraps a stable `ffdt.api` | S6.1, S6.2 | 7 / 11 | App runs baseline and compares presets; deployed if P1 time allows |
| SE7 | Documentation & Portfolio Packaging | Last, driven by frozen results | S7.1, S7.2 | 4.5 / 7.5 | Clean-clone reproduction; bullets, pitch, Q&A final |

## Critical path
`T1.1.1 -> T2.1.1 -> T2.1.3 -> T2.1.4 -> T3.1.3 -> T3.1.4 -> T3.1.5 -> T3.2.1 -> T3.2.5 -> T3.2.6 -> T4.1.3 -> T4.2.1 -> T5.1.1 -> T5.1.2 -> T5.2.1 -> T5.2.5 -> T7.2.2 -> T7.1.3`

Slack work (can float): T1.1.2, T2.1.2, T3.2.2, T3.2.4, T4.1.2, T6.x (after T3.2.6), T7.1.2.

## Stories
Full As-a / I-want / so-that text lives in `02_stories_and_tickets.md` (generated) and in `planning/tickets/`.

| Story | Sub-epic | Outcome |
|---|---|---|
| S1.1 | SE1 | Process and KPI vocabulary understood and cited |
| S1.2 | SE1 | Decisions and falsifiable hypotheses framed |
| S2.1 | SE2 | Every model input traceable |
| S3.1 | SE3 | Core stochastic line with state log |
| S3.2 | SE3 | Batches, changeovers, staffing, quality, QA release, OEE metrics |
| S4.1 | SE4 | Model verified; run length and replications justified |
| S4.2 | SE4 | Baseline frozen; face validity reviewed; baseline report |
| S5.1 | SE5 | Scenario matrix pre-registered and executed with CRN |
| S5.2 | SE5 | Statistics, sensitivity, bottleneck, memo |
| S6.1 | SE6 | Run and view KPIs in a browser |
| S6.2 | SE6 | Compare scenarios; share a link |
| S7.1 | SE7 | README, model card, reproducible release |
| S7.2 | SE7 | Slides, bullets, pitch, Q&A |

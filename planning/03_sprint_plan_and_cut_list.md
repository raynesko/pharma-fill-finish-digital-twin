# Week-by-week plan and cut list

Capacity: 8 weeks x about 9 h = 72 h. P0 = 61.5 h (85% of capacity), P1 = 10 h, P2 = 2 h. Weeks 1-7 hold only P0 work; week 8 is polish plus whatever P1 fits. If the builder can only commit 6 weeks (about 50 h), use the cut ladder below and expect the "Minimum viable" result.

Live version with hours per week: `BOARD.md`.

| Week | Theme | Tickets | Hours | Milestone at end of week |
|---|---|---|---|---|
| 1 | Domain + scaffold | T1.1.1, T1.1.2, T1.1.3, T3.1.1, T3.1.2 | 7.5 | Process map, glossary, hypotheses committed; repo scaffolded; ADR-001 decided. **Send SME outreach this week** |
| 2 | Parameters | T2.1.1, T2.1.2, T2.1.3, T2.1.4 | 8 | Benchmark CSV, assumptions, config validated |
| 3 | Core sim | T3.1.3, T3.1.4, T3.1.5 | 8 | Baseline week runs end to end |
| 4 | Operations layers | T3.2.1, T3.2.2, T3.2.3, T3.2.4, T3.2.5 | 10 | Changeovers, staffing, QA, quality, OEE metrics all working |
| 5 | Verify + baseline | T3.2.6, T4.1.1, T4.1.2, T4.1.3, T4.2.1, T4.2.3 | 9 | Baseline frozen at `baseline-v1.0`, report done |
| 6 | Scenarios + app start | T5.1.1, T5.1.2, T5.2.1, T5.2.3, T5.2.5, T6.1.1 | 9.5 | `results_final.json` frozen, memo written |
| 7 | App + docs + resume | T6.1.2, T6.2.1, T7.1.1, T7.1.3, T7.2.2 | 9.5 | v1.0.0 released; bullets final |
| 8 | P1 polish | T4.2.2, T5.2.2, T6.2.2, T6.2.3, T7.1.2, T7.2.1 (+ P2) | 10 (+2) | SME review, sensitivity, deployed app, slides |

Note: T5.1.1 is pre-registered at the start of week 6 and must be committed before T5.1.2 runs. If T5.2.2 (sensitivity) lands after the memo in week 8, re-read the memo against the tornado and amend the limitations.

## Cut ladder (cut in this order when behind; mark ticket status `cut`)
1. P2: T5.2.4 economics, T6.2.4 export.
2. T7.2.1 slides (README hero figure and resume bullets matter more).
3. T6.2.3 deploy + usability test (keep local app; record a screen capture instead).
4. T7.1.2 model card (fold limitations into README).
5. T6.2.2 usability polish.
6. T5.2.2 sensitivity: reduce to 4 parameters including sub-lot N. Do **not** drop entirely: it is the main defense against "your numbers are made up".
7. T4.2.2 face validation: keep a minimal advisor review.

**Do-not-cut list (project loses its credibility):** T2.1.1/T2.1.2 (sources and assumptions), T3.2.5 (OEE), T4.1.1-T4.1.3 (verification), T4.2.1 (baseline), T5.1.1 (pre-registration), T5.2.1 (paired statistics), T5.2.3 (bottleneck), T5.2.5 (memo).

## Minimum viable (about 50 h)
Everything in cut ladder items 1-5 dropped, T6.2.1 replaced by a notebook comparison table, staffing scenario kept only if T3.2.3 is done. Result: verified model, baseline, 4 scenarios with CIs, bottleneck, README, bullets. This still supports the resume line.

## Weekly ritual (15 minutes)
1. `python tools/build_index.py` and read `BOARD.md`.
2. Move any slipped ticket's `week` forward; re-check the cut ladder.
3. Commit with ticket IDs in the message.

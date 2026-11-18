# Baseline v1.0 definition

Ticket T4.2.1 · Frozen 2026-11-17 · Git tag `baseline-v1.0` · Config `configs/baseline_line.yaml`, version 1.0, **config hash `2f9b035c9964`** (`LineConfig.hash()`, the first 12 hex digits of the SHA-256 of the validated config).

## What "baseline" means
The baseline is the **as-is configured line**. It is a SIMULATED, BENCHMARK-PARAMETERIZED aseptic vial fill-finish line, **not a real plant and not plant data**. Its parameters come from public vendor and trade sources plus labeled engineering judgment (`data/raw/benchmark_sources.csv`, `docs/assumptions.md`). Every scenario is compared with this baseline as a paired difference under common random numbers. The baseline is a reference point for "what changes if...", not a forecast of any site's numbers.

## Line
| # | Station | Kind | Nominal rate (vpm) | Changeover scope | Failures (MTBF / MTTR mean, min) | Minor stops (every / lasting, min) |
|---|---|---|---|---|---|---|
| 1 | washer | machine | 350 | glass | 4,800 / 75 | 45 / 1.5 |
| 2 | tunnel | depyrogenation, 30 min residence | 350 | glass | 4,800 / 75 | none |
| 3 | filler | machine (reference station, D4) | 240 | full | 4,800 / 75 | 45 / 1.5 |
| 4 | capper | machine | 300 | packaging | 4,800 / 75 | 45 / 1.5 |
| 5 | avi | automated visual inspection | 300 | packaging | 4,800 / 75 | 45 / 1.5 |
| 6 | labeler | machine | 300 | packaging | 4,800 / 75 | 45 / 1.5 |
| 7 | cartoner | machine | 280 | packaging | 4,800 / 75 | 45 / 1.5 |
| - | manual re-inspection | offline pool, 1 unit per inspector | 5 per inspector | none | none | none |

Repair times are lognormal with CV 0.8. Failures are operation-dependent: the clock runs only while a station is running. Buffers between stations hold 2,000 vials (20 sub-lots of 100).

## Products, schedule and calendar
- **Products** prod_a, prod_b. **Formats** 2R and 10R vials.
- **Campaign** (fixed sequence, 6 × 100,000 = 600,000 vials): prod_a 2R, prod_a 2R, prod_a 10R, prod_b 10R, prod_b 10R, prod_b 2R. That gives 1 product change, 2 format changes and 2 same-product clearances at the filler.
- **Changeovers** (triangular low / mode / high, min): same-product clearance 45 / 90 / 150, format change 90 / 180 / 300, product change with full clean 390 / 600 / 900. Rolling: each station starts as soon as it finishes the batch.
- **Calendar**: 5 days × 2 shifts × 8 h, with a 60 min mid-shift break. Nothing runs, is repaired or is changed over off-shift. The campaign usually spills over the weekend, and this is kept and reported (amendment A2).

## Staffing and quality
- **Staff per shift**: 4 line operators (changeovers), 1 mechanic (repairs), 2 inspectors (manual re-inspection). Priority is repair > changeover > re-inspection.
- **Quality**:
  - Fill-weight rejects run at 0.1%, scrapped at the filler.
  - True defect incidence is 0.2%. AVI detects 85% of them and falsely rejects 1% of good vials.
  - Manual re-inspection confirms 95% of true defects as scrap and returns the rest upstream of the labeler.
- **QA**: 2 reviewers. Batch-record review is shifted-lognormal, minimum 480 min, mean 2,880 min. No release-testing hold (sterility incubation is not verified, so it is excluded). QA affects lead time only, never OEE (D5).

## Metrics (definitions: `docs/domain/glossary.md`, `docs/metrics_schema.md`)
- **Primary: good vials per scheduled-production hour** at the filler (`good_per_ppt_hour`, amendment A1), and **line OEE**.
- **Line OEE (D4)** = good vials packed / (scheduled production time × 240 vpm, the slowest nominal rate). It is shown as A × P × Q. Changeover and wait-for-staff count against Availability (D1, D2). Starved and blocked time counts against Performance and is reported separately (D3).
- **Experiment design** (`configs/experiment.yaml`): terminating campaign from an empty line, 30 replications, seed 20261116, 95% CIs.

## Verification at the tag
At the tag, all fast tests (161) and slow analytical checks (3) pass. The checks cover vial conservation, state-time sums, no-failure throughput, M/M/1 and M/M/1/K closed forms, availability and Little's Law. See `docs/verification.md`.

## Changelog
| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-11-17 | First frozen baseline. Any parameter change after this needs version 1.1 and a row here. |
| 1.0 (model fix E1) | 2026-11-17 | No parameter or config change; config hash still `2f9b035c9964`. Model fix for parallel units of one station (`UnitGroup` in `src/ffdt/sim/machine.py`, erratum E1 in `docs/scenario_matrix.md`). It only acts when a station has more than one unit, so the baseline (one AVI unit) is unaffected: all 30 baseline replications were re-run and are bit-identical to the pre-fix run. |
| 1.0 (metrics fix E2) | 2026-11-18 | No parameter or config change. Station-level `processed` was logged after the quality transform, so filler and AVI showed Q = 100% and AVI Performance was understated by about 1.2%. Fixed in `src/ffdt/sim/machine.py` (count vials before the transform); regression test `tests/unit/test_quality.py::test_station_rejects_reconcile_with_quality_ledger`. All 12 configurations re-run: replication summaries, loss Pareto and queue tables are bit-identical, so line metrics and every scenario comparison are unchanged. Only per-station A/P/Q tables changed. |

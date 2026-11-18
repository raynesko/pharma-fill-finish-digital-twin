# Model card: Pharma Fill-Finish Digital Twin

Ticket T7.1.2 · Structure loosely follows the ODD protocol for simulation models (overview, design concepts, details). **Simulated, benchmark-parameterized. Not plant data.** This card states no results; every result is in [`reports/results_final.json`](../reports/results_final.json).

## 1. Purpose
Decision-support exploration for a sterile liquid-vial fill-finish line: find which resource limits output and compare improvement options (inspection capacity, batch size, staffing, changeover reduction) against a frozen baseline with honest uncertainty. It is also a portfolio demonstration of operations-analysis method: pre-registration, common random numbers, multiple bottleneck methods.

## 2. Intended and non-intended use
| Intended | Not intended |
|---|---|
| Exploring *directions* and *relative sizes* of improvement levers on a generic line | Plant release, batch disposition or any GxP decision (the model is not a validated computerized system) |
| Teaching and discussing OEE, Theory of Constraints, queueing and changeover effects | Predicting a specific real line's output, OEE or lead time without calibration to its data |
| Framing questions to ask with real historian/MES data | Capital approval on its own: no costs are modeled |
| Interview and portfolio discussion | Regulatory submissions or claims about any company's process |

## 3. Overview
- **Entities:** sub-lots of 100 vials (configurable), carrying batch, product, format and defect counts ([ADR-001](adr/adr_001_entity_granularity.md)).
- **Resources:** 7 serial stations (washer, depyrogenation tunnel, filler/stopperer, capper, AVI, labeler, cartoner) with finite buffers; an offline manual re-inspection pool; staff pools of line operators (changeovers), mechanics (repairs) and inspectors (re-inspection); QA reviewers (batch release).
- **Scale and horizon:** one weekly campaign of 6 batches (2 products × 2 vial formats), 2 shifts × 8 h × 5 days with breaks; terminating simulation from an empty, cleared line until the last vial is packed and released.
- **Process:** each station draws a sub-lot from its input buffer, processes it at its nominal rate, may break down (operation-dependent failure clock, repair needs a mechanic) or minor-stop, and blocks when its output buffer is full. At batch boundaries each station changes over by its scope (product, format or same-product clearance) using operators. Quality: fill-weight rejects at the filler; AVI rejects go to manual re-inspection, which scraps confirmed defects and returns the rest.

## 4. Design concepts
- **Emergence:** starvation, blocking, the constraint and queue lengths are outputs, never inputs.
- **Stochasticity:** every random draw comes from a per-station, per-replication stream (`SeedSequence.spawn`), which makes common random numbers possible: a scenario changes one thing and every other station sees the same breakdowns and defects.
- **Observation:** a state ledger records every station's state interval, sub-lot output, buffer entry/exit and batch milestone. Metrics are computed only from the ledger (`ffdt.metrics` never imports the simulator). Definitions: [`docs/domain/glossary.md`](domain/glossary.md), schema: [`docs/metrics_schema.md`](metrics_schema.md).

## 5. Details
- **Parameters:** every value traces to [`data/raw/benchmark_sources.csv`](../data/raw/benchmark_sources.csv) or is tagged engineering judgment; full register in [`docs/assumptions.md`](assumptions.md).
- **Baseline:** v1.0, frozen at git tag `baseline-v1.0`, config hash `2f9b035c9964` ([`docs/baseline_definition.md`](baseline_definition.md)). Changes need v1.1 and a changelog row.
- **Experiment design:** 30 replications, seed 20261116 ([`configs/experiment.yaml`](../configs/experiment.yaml)); scenarios and decision rules pre-registered in [`docs/scenario_matrix.md`](scenario_matrix.md) and [`docs/domain/scenario_hypotheses.md`](domain/scenario_hypotheses.md).

## 6. Verification and validation
- **Verification** ([`docs/verification.md`](verification.md)): vial conservation at every instant, state-time accounting, determinism and stream isolation, analytical checks against M/M/1, M/M/1/K and availability theory, Little's Law bookkeeping, a known-bottleneck synthetic line, and regression tests for each model erratum.
- **Errata found and fixed:** E1 (parallel AVI units let a batch's last sub-lot overtake, causing spurious downstream changeovers) and E2 (station reject counts logged after the quality transform). Both are dated in [`docs/scenario_matrix.md`](scenario_matrix.md) and the baseline changelog; all runs were repeated.
- **Validation:** face validity only. No plant data was available; a practitioner review (T4.2.2) is pending. One-at-a-time sensitivity: [`reports/sensitivity.md`](../reports/sensitivity.md).
- **Reproducibility:** a clean clone regenerates `results_final.json` with every number identical.

## 7. Limitations
1. **No real line data.** Speeds, failure and repair times, changeover times and reject rates are public benchmarks or judgment; absolute numbers (OEE, vials per hour) are illustrative.
2. **One line, one product mix, one week.** A different mix, schedule or line layout could move the constraint.
3. **Simplified equipment:** no reduced-speed losses, no start-up scrap after changeovers, filler and stopperer modeled as one station, tunnel as a fixed-residence delay with backpressure.
4. **Staff:** no absenteeism, skills or travel time; one shared pool per role.
5. **Out of scope:** lyophilization, sterility-test holds, media fills, environmental-monitoring excursions, deviations and CAPA, material shortages.
6. **No costs:** options are ranked by output, not by return on investment.
7. **Changeover-reduction levels are assumptions** from a published case study, not measured SMED results.
8. **Local sensitivity only:** one-at-a-time ±20% does not explore interactions between parameters.

## 8. Version
Model and results as of 2026-11-18 (`results_final.json` frozen that day). Baseline v1.0. Package `ffdt` in `src/`; Python 3.12.

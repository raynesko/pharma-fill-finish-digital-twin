# Pre-registered scenario matrix

Ticket T5.1.1 · Written 2026-11-17, **before any scenario run**. Git history shows this file committed before `results/run_log.jsonl` has any scenario entry. Hypotheses, mechanisms and refutation conditions are in `docs/domain/scenario_hypotheses.md` (H1a-H5, amendments A1-A4). Every scenario is a YAML diff against frozen **baseline v1.0** (config hash `2f9b035c9964`, tag `baseline-v1.0`). SIMULATED, BENCHMARK-PARAMETERIZED LINE. NOT PLANT DATA.

## Matrix
| Scenario file | Family | Change vs baseline | Level justification | Hypotheses | Set |
|---|---|---|---|---|---|
| `sc01_avi_plus1` | SC-01 | AVI units 1 → 2 | Smallest capacity step (one machine) | H1a, H1b | main |
| `sc02_batch_x0p5` | SC-02 | 12 × 50,000 instead of 6 × 100,000 (each batch split in two) | Halving keeps mix, sequence and total exactly | H2a, H2b | main |
| `sc02_batch_x2` | SC-02 | 4 batches: identical neighbours merged (mean 150,000) | Largest batches possible at fixed mix, sequence and total (A3) | H2a, H2b | main |
| `sc03_operator_plus1` / `_minus1` | SC-03 | Line operators 4 → 5 / 3 | ±1 head per role, as pre-registered | H3a | main |
| `sc03_mechanic_plus1` | SC-03 | Mechanics 1 → 2 | +1 head. −1 is infeasible (A4) | H3a, H3b (see A4) | main |
| `sc03_inspector_plus1` / `_minus1` | SC-03 | Inspectors 2 → 3 / 1 | ±1 head | H3a | main |
| `sc04_changeover_m25` | SC-04 | Every changeover × 0.75 | Low end of SMED range B-021. **ASSUMPTION, not a measured SMED result** | H4a | main |
| `sc04_changeover_m50` | SC-04 | Every changeover × 0.50 | High end of B-021 ("up to 50%"). **ASSUMPTION** | H4a | main |
| `sc05_combo_co50_avi2` | SC-05 | Changeover × 0.50 and AVI units 1 → 2 | Combines the SC-04 high level and SC-01 | H5 | **exploratory** |

The main set has 10 comparisons; the exploratory set has 1.

## Metrics, fixed before any run
- **Primary:** good vials per scheduled-production hour at the filler (`good_per_ppt_hour`, amendment A1). It is reported as a paired difference vs baseline (scenario − baseline, matched by replication number under common random numbers), in absolute terms and as % of baseline.
- **Family-specific co-primary** (from the hypotheses):
  - changeover share of PPT (SC-02, SC-04)
  - wait-for-staff share of PPT (SC-03)
- **Secondary:**
  - line OEE with A / P / Q
  - mean batch lead time (SC-02 H2b)
  - mean queue time before AVI and before manual inspection (SC-01 H1b)
  - busiest station and the constraint after the change (T5.2.3)
  - makespan and weekend-spill share (A2)

## Decision rules (from the hypotheses, unchanged)
- **Test:** paired t-test on the 30 per-replication differences, two-sided, 95% CI.
- **Multiple comparisons:** Holm adjustment across the 10 main-set comparisons on the primary metric. SC-05 is reported unadjusted and labelled exploratory.
- **Practical significance:** at least +3% good vials per PPT hour, or +2 OEE points (TARGET). A result can be statistically significant without being practically significant, and the report says which applies.
- **Replications:** 30 per scenario, seed 20261116, replication r of every scenario paired with replication r of the baseline (`configs/experiment.yaml`).

## Run budget
12 configurations (baseline plus 11 scenarios) × 30 replications. The baseline takes about 9 s for 30 replications in parallel on the development machine (16 cores), and about 60 s on one core. Estimate: about 2 min in parallel and 12 min serial. Both are well under the 1 h target.

## Run order and outputs
`python tasks.py scenarios` runs baseline then every scenario in file-name order. It writes `results/<scenario>/<scenario>.{summary,stations,pareto,queues}.parquet`, with config hash and git SHA in the metadata, and appends one line per run to `results/run_log.jsonl`. Statistical comparison (T5.2.1) and bottleneck analysis (T5.2.3) read only these files.

## Amendments
**E1 (2026-11-17, after the first scenario run; model erratum).** The first full run (T5.1.2) showed `sc01_avi_plus1` *losing* output vs baseline (−1.6% good vials per PPT hour). Investigating that in T5.2.1 found a model defect, not a line effect: with two parallel AVI units, the last sub-lot of a batch could leave AVI before an earlier sub-lot of the same batch still in the other unit. The labeler then changed over to the next batch and had to change back for the straggler, adding spurious changeovers. Fix: a unit holding a batch's last sub-lot releases it only after its sibling units have released the rest of that batch (`UnitGroup`, `src/ffdt/sim/machine.py`), which is how line clearance works on a real parallel station. Regression test: `tests/unit/test_line.py::test_parallel_units_do_not_cause_spurious_downstream_changeovers`.
- **What changed:** model code only. No hypothesis, level, metric, decision rule, seed or replication count was changed.
- **Affected scenarios:** only those with more than one unit at a station: `sc01_avi_plus1` and `sc05_combo_co50_avi2`. All 12 configurations were re-run; baseline and the other 9 scenarios are bit-identical to the first run, which confirms the fix is confined to parallel units.
- **Disclosure:** the corrected sc01 result was produced after the pre-fix sc01 result had been seen. The fix was chosen because the pre-fix behaviour was physically wrong (a batch split across a changeover), not because of the direction of the result. The superseded run is kept locally in `results/_superseded_E1/` (results are not committed).

# Validation and metrics plan

Terminology follows Sargent (2013) and Law (Simulation Modeling and Analysis): **verification** = built right, **validation** = right model. Because no real plant data is used, validation here is limited to **face validity, sensitivity and reference-range plausibility**. The README must say this in plain words. (Verify citation details before quoting in the README.)

## 1. Baseline definition
Baseline v1.0 is the frozen "as-is" configured line (T4.2.1): 8 stations, 2 products x 2 formats, one fixed one-week campaign (batch list in `configs/baseline_line.yaml`), staffing pools per role, benchmark-derived stochastic parameters. It is a reference, not a real plant. Tag `baseline-v1.0`; any change means v1.1 plus a changelog.

## 2. Simulation design
- **Mode:** terminating campaign (start empty and clean, run until all batches packed). Steady-state mode used only for verification.
- **Replications:** n from a pilot (T4.1.3) so the 95% CI half-width is at most 2% of the mean (TARGET).
- **Randomness:** one `numpy.random.SeedSequence` spawn per station and per replication for common random numbers (CRN).

## 3. Metrics (definitions in `docs/domain/glossary.md`)
| Metric | Level | Formula / note |
|---|---|---|
| Availability | station, line | Run-capable time / planned production time; breakdowns, minor stops, changeovers, wait-for-staff reduce it |
| Performance | station | Actual output / (operating time x nominal rate); minor stops, starvation, blocking reported as separate loss categories though all count in Performance (glossary D3) |
| Quality | station, line | Good / total started; AVI rejects, in-process rejects |
| OEE | station, line | A x P x Q; line OEE computed on the constraint's ideal rate (decision documented in T1.1.2) |
| Good vials per hour | line | Primary throughput metric |
| Utilization | station | Busy fraction of planned time |
| Queue time and length | buffer | Time-weighted; checked against Little's Law |
| Batch lead time | batch | Start to QA release; excludes equipment OEE |
| Changeover share | line | Changeover hours / planned hours |

## 4. Verification (T4.1.x)
Invariants (conservation, state-time sums, determinism), no-failure throughput equals the bottleneck rate, M/M/1 and M/M/1/K closed forms, availability formula MTBF/(MTBF+MTTR), Little's Law per buffer, coverage target 90% on `ffdt.sim`.

## 5. Face validity and plausibility (T4.2.2, T2.1.1)
- Practitioner or advisor walk-through with a 5-item checklist (flow, rates, downtime magnitude, changeover, QA hold).
- Baseline OEE is compared to a **sourced** reference band. OEE definitions differ across sources; the comparison is "plausible/explained", never "matched". World-class OEE of about 85% is widely cited in TPM literature, but pharma lines typically run well below it; the specific pharma figure must come from a source found in T2.1.1 (do not quote from memory).

## 6. Scenario comparison method (T5.1.x, T5.2.1)
- Scenarios are pre-registered (T5.1.1) as YAML diffs with primary and secondary metrics fixed beforehand.
- Run each scenario with the **same n seeds as baseline** (CRN). Compute per-replication differences d_i = scenario_i - baseline_i.
- Report mean(d), t-based 95% CI, a bootstrap CI cross-check, and a Holm adjustment across the pre-registered scenarios. Show paired vs unpaired CI width to demonstrate the CRN gain.
- Practical-significance threshold: 2 OEE points or 3% good vials/hour (TARGETS, chosen to exceed typical CI width, adjustable with justification before running).
- Label any non-pre-registered comparison as exploratory.

## 7. Sensitivity analysis (T5.2.2)
One-at-a-time +/-20% on at least 8 parameters: MTBF, MTTR, filler speed, AVI speed, false-reject rate, changeover duration, batch size, sub-lot size N. Output tornado charts for line OEE and good vials/hour; record which parameters flip the bottleneck or reorder scenario ranks. Optional (only if ahead): Latin hypercube with rank correlation.

## 8. Bottleneck identification (T5.2.3)
At least three methods (utilization, active-period method after Roser et al., blocking/starvation signature) plus queue build-up as corroboration; unit-tested on a synthetic line with a known constraint. State that with random failures the constraint moves, so the claim is "the station that is the constraint most often and for the largest share of time".

## 9. Numbers that may appear on the resume
All come from `reports/results_final.json`; none exist yet. Each needs the qualifier "simulated, benchmark-parameterized line".
1. **Baseline line OEE** with 95% CI and n replications.
2. **Identified constraint** station name with its utilization and share of time it was the constraint.
3. **Best scenario effect:** change in good vials/hour (%) and OEE points with 95% CI, and how many scenarios were compared.
4. **Verification count:** number of automated tests and the analytical-check error (for example M/M/1 within x%).
5. Optional: **usability:** number of non-technical reviewers who completed the task, and the time.

Forbidden on the resume: any claim of plant data, any dollar savings not labeled illustrative, any OEE figure without a CI, any comparison not pre-registered unless labeled exploratory.

# Sensitivity analysis

Ticket T5.2.2. **Simulated, benchmark-parameterized. Not plant data.** Every number is a RESULT from `results/sensitivity.json` (`python -m ffdt.experiments.sensitivity`). One parameter at a time is moved to -20% and +20% of its baseline v1.0 value (sub-lot size N to 10 and 200 vials), with 30 replications each, paired with the baseline replications (common random numbers). Figures: `reports/figures/tornado_throughput.png`, `reports/figures/tornado_oee.png`.

Deviation from plan: N = 500 was planned, but ADR-001 requires each 2,000-vial buffer to hold at least 10 sub-lots, so 200 is the largest valid level without also changing the buffers.

## Which parameters matter (good vials per scheduled hour)
| Parameter | Assumption | Level | Change (95% CI) | Line OEE change, points | Bottleneck |
|---|---|---|---|---|---|
| Filler speed | A-030 | -20% | -12.1% (-12.6 to -11.7) | +5.6 | filler |
| Filler speed | A-030 | +20% | +7.7% (+7.2 to +8.1) | -4.4 | filler |
| Changeover durations | A-038 | -20% | +8.7% (+8.4 to +8.9) | +5.0 | filler |
| Changeover durations | A-038 | +20% | -7.5% (-7.6 to -7.3) | -4.3 | filler |
| Batch size (6 batches; total volume moves with it) | A-039 | -20% | -8.4% (-8.9 to -7.8) | -4.8 | filler |
| Batch size (6 batches; total volume moves with it) | A-039 | +20% | +6.6% (+6.2 to +7.0) | +3.8 | filler |
| AVI speed | A-033 | -20% | -1.3% (-1.5 to -1.1) | -0.7 | filler |
| AVI speed | A-033 | +20% | -0.1% (-0.1 to +0.0) | -0.0 | filler |
| Time between breakdowns (MTBF) | A-035 | -20% | -0.9% (-1.4 to -0.4) | -0.5 | filler |
| Time between breakdowns (MTBF) | A-035 | +20% | +0.4% (-0.1 to +0.9) | +0.2 | filler |
| Repair time (MTTR) | A-036 | -20% | +0.7% (+0.5 to +1.0) | +0.4 | filler |
| Repair time (MTTR) | A-036 | +20% | -0.8% (-1.0 to -0.5) | -0.4 | filler |
| Buffer capacity | A-021 | -20% | -0.7% (-0.7 to -0.6) | -0.4 | filler |
| Buffer capacity | A-021 | +20% | +0.6% (+0.6 to +0.7) | +0.4 | filler |
| Time between minor stops | A-037 | -20% | -0.4% (-0.5 to -0.3) | -0.2 | filler |
| Time between minor stops | A-037 | +20% | +0.3% (+0.2 to +0.4) | +0.2 | filler |
| Sub-lot size N (10 / 200 vials) | A-001 | N = 10 | +0.4% (+0.3 to +0.5) | +0.2 | filler |
| Sub-lot size N (10 / 200 vials) | A-001 | N = 200 | -0.0% (-0.1 to -0.0) | -0.0 | filler |
| AVI false-reject rate | A-040 | -20% | +0.0% (+0.0 to +0.1) | +0.0 | filler |
| AVI false-reject rate | A-040 | +20% | -0.0% (-0.0 to -0.0) | -0.0 | filler |
| Defect incidence | A-040 | -20% | +0.0% (+0.0 to +0.0) | +0.0 | filler |
| Defect incidence | A-040 | +20% | -0.0% (-0.0 to -0.0) | -0.0 | filler |
| QA review time (lead time only) | A-042 | -20% | +0.0% (+0.0 to +0.0) | +0.0 | filler |
| QA review time (lead time only) | A-042 | +20% | +0.0% (+0.0 to +0.0) | +0.0 | filler |

## What survives and what does not
- **The constraint.** The filler stays the constraint under every perturbation (three run-level methods).
- **The main recommendation.** Changeover reduction beats a second AVI machine under every perturbation of filler and AVI speed (the parameters most able to move the constraint):
  - Filler speed -20%: changeover -50% +20.9% vs second AVI +0.1% (95% CI -0.3 to +0.4); constraint with the second AVI: filler.
  - Filler speed +20%: changeover -50% +27.5% vs second AVI +0.6% (95% CI +0.3 to +1.0); constraint with the second AVI: filler.
  - AVI speed -20%: changeover -50% +24.6% vs second AVI +1.7% (95% CI +1.3 to +2.0); constraint with the second AVI: filler.
  - AVI speed +20%: changeover -50% +24.9% vs second AVI +0.4% (95% CI +0.2 to +0.7); constraint with the second AVI: filler.
- **OEE and output move in opposite directions for Filler speed:** at -20% output -12.1% but line OEE +5.6 points; at +20% output +7.7% but line OEE -4.4 points. Line OEE is measured against the filler's own nominal speed (D4), so changing that speed moves the yardstick. Compare options on output, not on OEE alone.
- **Parameters that move throughput by 3% or more** at ±20%: Filler speed, Changeover durations, Batch size (6 batches; total volume moves with it). These are where real line data would matter most.
- **Parameters that move it by less than 1%:** Time between breakdowns (MTBF), Repair time (MTTR), Buffer capacity, Time between minor stops, Sub-lot size N (10 / 200 vials), AVI false-reject rate, Defect incidence, QA review time (lead time only).
- **Discretization (sub-lot size N).** N = 10 changes throughput by +0.40% and N = 200 by -0.03% against the default N = 100.

## Caveats
- One-at-a-time ±20% shows local sensitivity around the baseline; it does not show interactions between parameters.
- Batch size ±20% keeps 6 batches, so total weekly volume moves with it; good vials per scheduled hour is a rate, so it stays comparable.
- QA review time affects batch lead time only; it is included for completeness and cannot move OEE or throughput (QA never blocks the line, A-014).

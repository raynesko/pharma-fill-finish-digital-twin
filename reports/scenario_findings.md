# Fill-finish line: what limits output and what to do first

*Memo for the plant manager · Simulated, benchmark-parameterized. Not plant data. Every number is a RESULT from `reports/results_final.json` (frozen 2026-11-18); its `sources` block names the run files. Baseline v1.0, 30 replications per scenario, common random numbers.*

## Bottom line
- **The filler is the constraint.** All 4 bottleneck methods agree, and no scenario tested moves it. It is the sole bottleneck 62% of scheduled time; the cartoner is a secondary, shifting bottleneck (in 30 of 30 runs).
- **Changeovers are the biggest loss:** 27% of the filler's scheduled time. Line OEE is 57% (95% CI 56.4 to 58.2).
- **Do first: a SMED changeover-reduction project.** A 25% cut gives +11.1% good vials per scheduled hour, 50% gives +24.8%. The reduction levels are assumptions, not measured SMED results.
- **Do not buy a second AVI machine for output:** +0.2%, not significant. AVI is not the constraint.

## Ranked options (main pre-registered set, Holm-adjusted)
Change in good vials per scheduled-production hour vs baseline (8,252/h), paired 95% CI. Practical significance is a TARGET of +3%.

| Rank | Option | Effect (95% CI) | Holm p | Practical? | Batch lead time |
|---|---|---|---|---|---|
| 1 | Cut every changeover by 50% (SMED, ASSUMPTION) | +24.8% (+24.0% to +25.5%) | <0.001 | yes | -5.4 h |
| 2 | Cut every changeover by 25% (SMED, ASSUMPTION) | +11.1% (+10.8% to +11.4%) | <0.001 | yes | -4.4 h |
| 3 | Merge identical neighbouring batches (4 batches) | +5.9% (+4.4% to +7.4%) | <0.001 | yes | +8.5 h |
| 4 | One more line operator | +3.5% (+3.0% to +4.0%) | <0.001 | yes | -3.1 h |
| 5 | Add a second AVI machine | +0.2% (-0.1% to +0.6%) | 0.85 | no | +0.0 h |
| 6 | One more mechanic | +0.1% (+0.0% to +0.1%) | 0.92 | no | +0.0 h |
| 7 | One fewer manual inspector | +0.0% (+0.0% to +0.0%) | 0.92 | no | +0.4 h |
| 8 | One more manual inspector | +0.0% (+0.0% to +0.0%) | 0.92 | no | +0.0 h |
| 9 | One fewer line operator | -5.2% (-5.6% to -4.9%) | <0.001 | yes | +4.1 h |
| 10 | Halve batch size (12 x 50,000 vials) | -16.9% (-18.3% to -15.6%) | <0.001 | yes | +27.3 h |

Exploratory, not adjusted: changeover -50% plus a second AVI gives +25.6%, only +0.7% more than changeover -50% alone.

## What to do, in order
1. **SMED on the line changeover.** It attacks the constraint's largest loss. Shorten changeovers at every station, not only the filler: at -50% the filler's scheduled time falls 1.45x as much as its own changeover time does, because shorter downstream changeovers stop blocking it.
2. **Add one line operator** (+3.5%). Operator waits are concentrated at the packaging end: the cartoner waits for staff 13% of its scheduled time. Do not cut one (-5.2%).
3. **Keep batches large where the schedule allows.** Merging identical neighbouring batches gives +5.9% but adds 8.5 h of batch lead time. Halving batches changes output by -16.9% and adds 27.3 h, because QA release queueing grows 34 h.
4. **Not worth it for output:** a second AVI, a mechanic, or an inspector (no significant effect). They may still be justified for quality or risk reasons this model does not value.

## What the study got wrong in advance (pre-registered hypotheses)
- H3a (refuted as registered): Wait-for-staff at the filler is 0.22% of PPT, yet +1 operator gives +3.5%. The waits sit downstream: cartoner 12.6% of its PPT (6.1% with +1 operator). The pre-registered test measured staff waits at the wrong station.
- H2b (refuted as stated: not monotonic): Lead time rises at both levels. Merging batches adds cycle time (+8.7 h); halving batches cuts cycle time (-7.6 h) but QA release queueing grows +34.5 h, so QA release becomes the lead-time constraint.
- H4a (monotonic: supported; less than proportional: refuted, mechanism found): Filler run time is unchanged; its scheduled time falls 866 min at -50%, 1.45x its own changeover saving (596 min), because shorter downstream changeovers also cut the filler's blocked time (247 min). The minute accounting reconciles, so this is not an accounting error.
- Supported: H1a, H2a, H5 (exploratory). Mixed: H1b. Not testable: H3b. Not examined: H4b. Full list in `reports/results_final.json`.

## Limitations
- **Simulated, benchmark-parameterized.** Speeds, failure and changeover times come from public benchmarks and engineering judgment (`data/raw/benchmark_sources.csv`), not from a plant. Face validation by a practitioner is still pending (T4.2.2).
- **SMED levels are assumptions.** The -25%/-50% levels follow a published case study (up to 50%, source B-021); the achievable cut on a real line must be measured.
- **One product mix and one week.** Six batches, two products, two vial formats, two shifts on five days. A different mix or schedule could move the constraint.
- **Out of scope:** lyophilization, sterility-test holds, media fills, deviations. No costs are modeled, so the ranking is by output, not by return on investment.
- **Two model errata were found and fixed during the study** (E1 parallel AVI units, E2 station reject counts); both are documented, and all runs were repeated after the fixes.

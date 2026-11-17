# Scenario hypotheses and decision questions (pre-registration)

Ticket T1.1.3 · Written **before any model code or scenario run**. After the first scenario run, edit only by appending dated amendments at the bottom. Terms follow `glossary.md`. Every expected direction below is a **HYPOTHESIS** from theory, not a result.

**No bottleneck is pre-committed.** The constraint is an output of the baseline model (T5.2.3). Each hypothesis is therefore conditional: it states what should happen *if* a given station is, or is not, the constraint, which makes it falsifiable and also a check on the model itself.

**Decision rules fixed in advance** (see `planning/04_validation_and_metrics_plan.md`)
- Primary metric for all scenarios unless stated: **good vials per hour** (line), paired difference vs baseline v1.0 with 95% CI, common random numbers.
- Practical significance: at least +3% good vials/h or +2 OEE points (TARGET; may be changed only before the first run, with a dated amendment).
- Secondary metrics: line OEE (A/P/Q), constraint utilization, batch lead time, mean queue time at the buffer upstream of the changed resource.
- Multiple comparisons: Holm adjustment across all scenarios below.

## SC-01 Add an inspection station
- **Decision question:** Would a second automated inspection station (or added inspection capacity) raise output enough to justify the capital?
- **Mechanism (Theory of Constraints):** Added capacity helps only at the constraint. If inspection is the constraint, filler-side buffers should be blocked often and AVI utilization highest; adding capacity should raise throughput until the next resource binds. If inspection is not the constraint, extra capacity only moves a queue.
- **HYPOTHESIS H1a:** throughput increases (positive effect) **if and only if** the AVI station is the baseline constraint by at least two of the three bottleneck methods.
- **HYPOTHESIS H1b:** AVI re-inspection queue time falls in all cases (more capacity shortens its queue regardless of the constraint).
- **Primary metric:** good vials/h. Secondary: AVI queue time, constraint after change.
- **Refuted if:** (a) AVI is the constraint at baseline but the throughput CI includes 0 and no other station becomes starved-limited, or (b) AVI is not the constraint but throughput rises beyond practical significance (this would indicate a model or analysis error and must be investigated before reporting).

## SC-02 Batch size (x0.5 and x2 of baseline batch sizes)
- **Decision question:** Do larger campaigns buy output by amortizing changeovers, and what do they cost in lead time?
- **Mechanism:** Fewer batches per week means fewer changeovers (availability gain), but longer batch cycle time and, with finite QA reviewers, burstier arrivals to QA.
- **HYPOTHESIS H2a:** larger batches (x2) raise good vials/h and shrink changeover share; smaller (x0.5) do the opposite. The magnitude scales with the baseline changeover share (if changeover share is under about 5% of PPT, the effect should be below practical significance).
- **HYPOTHESIS H2b:** batch lead time increases with batch size.
- **Primary metric:** good vials/h and changeover share. Secondary: batch lead time.
- **Refuted if:** x2 shows no positive throughput effect while changeover share exceeds 10% of PPT, or if x2 shortens lead time.
- **Design note:** hold total vials per week fixed across levels so only batch count changes.

## SC-03 Staffing (plus or minus one in each role: operator, mechanic, inspector)
- **Decision question:** Where is the next head worth more than it costs?
- **Mechanism:** Staff matter only when jobs queue for them: mechanics when repairs overlap, inspectors for re-inspection, operators for changeovers and interventions. Removing a head from a role with spare capacity should do little.
- **HYPOTHESIS H3a:** the effect of +1 on a role is positive only if baseline wait-for-staff time for that role is a visible loss (at least 1% of PPT, TARGET threshold).
- **HYPOTHESIS H3b:** -1 mechanic causes the largest degradation of availability, because repair delays compound.
- **Primary metric:** good vials/h and wait-for-staff share of PPT.
- **Refuted if:** +1 on a role with near-zero baseline wait time produces a practically significant throughput gain.

## SC-04 Changeover time reduction (-25% and -50%, SMED-style)
- **Decision question:** Is a SMED project worth pursuing, and how much of the reduction survives to output?
- **Mechanism:** Changeover is an availability loss. If the changing station is the constraint (or the changeover blocks the whole line), saved minutes become output; if a non-constraint changes over while the constraint is still busy, saved minutes are partly absorbed in buffers.
- **HYPOTHESIS H4a:** throughput gain is monotonic in reduction level and less than proportional to the saved changeover share (absorbed by buffers and non-constraint slack).
- **HYPOTHESIS H4b:** the benefit is larger when batches are small (SC-02 interaction), to be examined only exploratorily.
- **Assumption flag:** the reduction percentages are assumptions, not measured SMED outcomes.
- **Primary metric:** good vials/h and changeover share. Secondary: line OEE availability.
- **Refuted if:** the throughput gain equals or exceeds the saved changeover share (impossible in a sound model, so it would signal an accounting error).

## SC-05 Combination: changeover -50% plus added inspection station
- **Decision question:** Are the two levers complementary, redundant or conflicting?
- **Mechanism:** If inspection is the constraint at baseline, changeover savings are partly wasted (more arrivals at a saturated AVI), and adding AVI alone leaves changeover loss in place; together they should beat either alone. If another station is the constraint, neither may matter.
- **HYPOTHESIS H5:** if AVI is the baseline constraint, combined effect exceeds the larger single effect by a practically significant amount (super-additive or at least additive); if AVI is not the constraint, combined effect is approximately that of SC-04 alone.
- **Primary metric:** good vials/h compared with SC-01 and SC-04 alone. Interaction test is **exploratory** (not Holm-adjusted with the main set; label it so).
- **Refuted if:** combined effect is less than the larger single effect with a CI excluding 0.

## What would change the plan
- If baseline shows no station with persistent starvation/blocking signature, add a note and keep all scenarios; report that no resource dominates.
- If a scenario is infeasible to run (runtime budget), drop in the order: SC-05, SC-02 x0.5, then request an amendment.

## Review checklist
- [x] At least 5 scenarios including the four required levers
- [x] Each has question, mechanism, directional HYPOTHESIS, primary metric, refutation condition
- [x] States that no bottleneck is pre-committed
- [x] Committed to git before any scenario run (first commit, 2026-11-17; no scenario has been run)

## Amendments
**A1 (2026-11-17, before any scenario run).** The primary metric "good vials per hour" is defined as **good vials packed per hour of scheduled production time (PPT) at the reference station (filler)**, the column `good_per_ppt_hour` in `docs/metrics_schema.md`. Rationale: in a 20-replication baseline pilot (T4.1.3), the per-calendar-hour variant had a CV of 16%. That variance is driven by whether the campaign spills over the weekend (25 of 30 replications did), not by line performance. The PPT-hour variant had a CV of 3.5%. The choice was made from baseline variance only; no scenario had been run. Decided by the project owner.

**A2 (2026-11-17, before any scenario run).** The baseline keeps the 6-batch campaign (A-039) even though it usually does not finish within one 5-day week. Weekend spill is reported as a baseline finding (makespan and spill probability are secondary metrics), not designed away. Decided by the project owner.

**A3 (2026-11-17, before any scenario run).** SC-02 "x2" cannot be built while holding total vials, product mix and sequence fixed: the baseline mix has two single-batch runs (prod_a 10R, prod_b 2R). The x2 level is therefore realized as the largest batches that keep all three fixed, merging identical neighbours into 4 batches (mean 150,000 vials, x1.5). That removes the two same-product clearances and leaves format and product changes unchanged. The x0.5 level (12 × 50,000) is exact. H2a/H2b are tested on these realized levels. File: `configs/scenarios/sc02_batch_x2.yaml`.

**A4 (2026-11-17, before any scenario run).** "Mechanic −1" means 0 mechanics, since the baseline has 1. With zero mechanics, repairs never start and a campaign with a breakdown cannot finish (T3.2.3 test), so the level is infeasible and is not run. H3b ("−1 mechanic causes the largest degradation") cannot be tested as written. It is reported as **not testable at baseline staffing**, not as supported. Operator and inspector −1 run as planned.

**Disclosure (2026-11-17).** Before this matrix was committed, while testing the dashboard (T6.1.2), a 2-replication run with two AVI units (everything else at baseline) was rendered as a timeline chart. It showed both AVI units mostly starved during one sample shift. An automated dashboard test also builds charts for a small 10,000-vial-batch configuration with two AVI units and 2 operators; its numbers were never inspected. This was a user-interface check, not a scenario run: it was not saved, compared or tested. No hypothesis, level or decision rule was changed because of it. Baseline-only runs (pilot, verification, dashboard) were also seen before pre-registration. That is allowed, since hypotheses H1a-H5 are conditional on the baseline constraint.

# Project Charter: Pharma Fill-Finish Digital Twin

Version 1.0 · Status: approved for build · All numeric values labeled **TARGET**, **PLACEHOLDER** or **ASSUMPTION** are plans, not results.

## 1. Problem statement
Sterile injectable fill-finish lines are among the most capital-intensive and tightly regulated assets in pharma. Output is limited less by nominal machine speed than by stochastic downtime, changeovers and line clearance, inspection capacity, staffing, and batch-release hold times. Decisions such as adding an inspection station, resizing batches, adjusting staffing, or investing in changeover reduction (SMED) are usually made on intuition or spreadsheet averages, which ignore queueing, blocking and starvation. This project builds a discrete-event simulation of a vial fill-finish line, verifies it, and uses it to rank improvement levers and identify the bottleneck with quantified uncertainty.

## 2. Target user and business context
- **Primary user (persona):** a continuous-improvement or manufacturing engineer at a sterile-injectables site who must justify a change to a plant manager.
- **Secondary user:** a non-technical reviewer (hiring manager, plant manager) who can open a web app, change parameters and read the KPIs.
- **Context:** a single liquid-vial aseptic line running campaigns of batches across two products and two vial formats, in a GMP environment (21 CFR 210/211, EU GMP Annex 1 2022). The model is a decision-support exploration tool, not a validated GxP system.
- **Builder's purpose:** a portfolio piece for NJ operations, process-improvement and quality-analyst roles. It must show OEE fluency, changeover and queueing intuition, GMP awareness, and honest quantification against a baseline.

## 3. Objectives
1. Model 8 stations (washing, depyrogenation, filling, stoppering/capping, automated visual inspection with manual re-inspection, labeling, packaging/serialization) plus a QA batch-release queue.
2. Include stochastic breakdowns and minor stoppages, three changeover types, batch sizes, staffing pools and QA hold.
3. Report throughput, OEE (A/P/Q), utilization, queue times and batch lead time with 95% confidence intervals.
4. Verify the simulator with invariant and analytical tests; freeze a documented baseline.
5. Run a pre-registered scenario study (add inspection station, batch size, staffing, changeover reduction, one combination) with paired statistics and sensitivity analysis.
6. Deliver a Streamlit what-if app usable by non-technical reviewers.

## 4. Scope
**In scope:** liquid-filled vials; one line; terminating campaign simulation (one production week as the primary horizon, ASSUMPTION); sub-lot entities (default 100 vials, see ADR-001); OEE per Nakajima's six big losses; Python, SimPy, pandas, scipy, pydantic, Streamlit, plotly.

## 5. Explicit non-goals
- Lyophilization, formulation/compounding, terminal sterilization, isolator decontamination cycles, media-fill (aseptic process simulation) scheduling beyond a generic planned stop.
- Real plant data, MES/historian integration, or any claim that results predict a specific site.
- Cost-optimal design or a full business case (T5.2.4 is illustrative only, P2).
- Environmental-monitoring excursions, deviations/CAPA workflows, and quality-system modeling.
- GAMP 5 / CSV validation of the tool itself; the model card says plainly it is not for GxP decisions.

## 6. Success metrics (all TARGETS)
| Metric | Target | Why this number |
|---|---|---|
| Verification tests passing | 100% in CI | Non-negotiable for credibility |
| Sim vs M/M/1 mean wait | within 2% over 30+ reps | Standard analytic sanity check; tight enough to catch logic bugs |
| Little's Law error per buffer | < 1% | Identity must hold |
| 95% CI half-width, OEE and throughput | <= 2% of mean | Makes scenario differences of a few points detectable |
| Scenarios evaluated with paired CIs | >= 5 plus one combination | Covers the four required levers |
| Sensitivity parameters | >= 8, incl. sub-lot size N | Exposes discretization and assumption risk |
| Baseline replication runtime | < 10 s; app quick mode < 30 s | Interactive use |
| Non-technical reviewers finishing the task | >= 2 in <= 5 min unaided | Proves usability claim |
| Benchmarked parameters | >= 25 rows with source or judgment tag; 0 orphan config values | Auditability |
| Clean-clone reproduction | `make all` reproduces `results_final.json` | Reproducibility |

## 7. Parameters (sourced or tagged in T2.1.1; see `data/raw/benchmark_sources.csv`)
The original seed placeholders were replaced on 2026-11-16 by ranges from vendor datasheets and trade sources, with modes chosen by documented engineering judgment (23 of 37 rows are judgment-tagged; confidence is mostly L). Baseline modes are inputs to a model whose results are **not** tuned to hit any OEE reference.
| Station | Nominal rate mode (vpm) | Row | Basis |
|---|---|---|---|
| Vial washer | 350 | B-001 | Vendor range 50-400; mode judgment |
| Depyrogenation tunnel | 350 (30 min residence) | B-002, B-010 | Weak source; judgment |
| Filler + stoppering | 240 | B-003, B-004 | Vendor range 60-500; mode judgment |
| Capper | 300 | B-005 | Judgment |
| Automated visual inspection | 300 | B-006 | Vendor range 20-600; judgment |
| Manual re-inspection | 5 per inspector | B-007 | Derived from 5 s per background |
| Labeler | 300 | B-008 | Judgment |
| Cartoner / serializer | 280 | B-009 | Judgment |
The filler has the lowest nominal rate by design (downstream stations are specified with margin, as vendors size lines), so any constraint beyond the filler must emerge from downtime, changeovers, inspection loops, staffing or QA. No bottleneck is assumed.

## 8. Assumptions (summary; full register in docs/assumptions.md)
- Failures occur only while a machine is running (operation-dependent), per Law/Banks guidance on input modeling.
- Time unit minutes, rates in vials/min; sub-lot discretization accepted subject to the N sensitivity run.
- Infinite upstream supply of clean vials; no operator absenteeism; no material shortages.
- Changeover is an availability loss in OEE; QA hold is excluded from equipment OEE and reported as lead time.
- OEE reference ranges vary by source and definition; none is used as a "match" target, only for plausibility.

## 9. Key risks and mitigations
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Parameters read as invented | M | H | Benchmark CSV with confidence grades; judgment tags; sensitivity on every judgment value |
| Model complexity exceeds 72 h | H | H | P0/P1/P2 tiers; cut ladder in planning/03; P0 is 61.5 h |
| Runtime too slow for the app | M | M | ADR-001 granularity decision; cache; quick mode |
| Results look like cherry-picking | M | H | Pre-registered scenarios and metrics; Holm correction; sensitivity |
| No SME for validation | M | M | Face validation falls back to advisor plus structured self-review; limits stated |
| Domain errors (terminology, GMP) | M | H | Flag uncertain items instead of guessing; SME list in T1.1.1; verify citations before README |
| Scope creep into lyophilization or CAPA | M | M | Non-goals list enforced at ticket review |

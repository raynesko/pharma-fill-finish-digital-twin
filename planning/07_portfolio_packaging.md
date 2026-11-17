# Portfolio packaging

All bracketed values `[X]` are filled only from `reports/results_final.json` after T5.2.5. Never publish a bullet with placeholders.

## Resume bullets (drafts: Action + method + quantified result)
1. Built a discrete-event simulation (Python/SimPy) of an 8-station aseptic vial fill-finish line with stochastic downtime, three changeover types, staffing pools and QA release, parameterized from published benchmarks; baseline line OEE of [X]% (95% CI [a-b], [n] replications).
2. Identified [station] as the line constraint ([U]% utilization, constraint [S]% of run time) using three bottleneck methods, then ranked [k] pre-registered improvement scenarios with paired common-random-number comparisons: [best scenario] raised good output by [Y]% ([CI]) and OEE by [Z] points.
3. Delivered a Streamlit what-if tool letting non-technical users change batch size, staffing and changeover time to see OEE, throughput and queue times; verified with [N] automated tests including M/M/1 and Little's Law checks (within [e]%) and usability-tested with [m] reviewers.

Disclosure line for the project entry (not the bullet): "Simulated line parameterized from public benchmarks; no plant data."

## 60-second interview pitch (fill in numbers)
"Sterile fill-finish lines are expensive, and improvements like adding an inspection station or cutting changeover time are usually justified with averages that ignore queueing. I built a simulation of a vial fill-finish line, with breakdowns, changeovers, staffing and QA release, using published benchmarks because I did not have plant data. I verified it against queueing theory and Little's Law, froze a baseline at [X]% OEE, and ran pre-registered scenarios. The constraint turned out to be [station], and [scenario] gave the biggest gain, [Y]% more good vials, with a confidence interval, while [other scenario] did nothing because the constraint just moved. I also built a web app so a plant manager can try their own what-ifs. What I would do next with real data is calibrate downtime distributions from the historian."

## 5-slide summary outline (T7.2.1)
1. **Context and question:** why fill-finish is capacity-constrained; the decision (inspection, batch size, staffing, changeover).
2. **Line and model:** flow diagram, what is stochastic, what is out of scope; one sentence on GMP touchpoints (line clearance, QA release).
3. **Trust:** verification tests, analytical checks, face validity, sensitivity; honest limits.
4. **Results:** baseline OEE with Pareto of losses; bottleneck evidence; scenario forest plot with CIs.
5. **Recommendation and next steps:** what to do first, what would change the answer, how real data would be used.

## Interview Q&A with talking points (operations hiring manager)
| Question | Talking points |
|---|---|
| Why OEE and how did you define it? | A x P x Q; changeover as availability loss; starvation/blocking separated so performance is not a dumping ground; line OEE defined against the constraint; definitions differ across sources so I documented mine |
| How do you know the simulation is right? | Verification vs validation; conservation tests, M/M/1, Little's Law; face validity only, no plant data; sensitivity shows which assumptions matter |
| Where did the numbers come from? | Benchmark CSV with confidence grades; judgment values tagged and stress-tested; I would calibrate with historian data |
| What was the bottleneck and was it stable? | Report three methods; failures make it dynamic; which scenarios shifted it |
| Why did a scenario not help? | Theory of Constraints: improving a non-constraint adds WIP, not output |
| How would SMED apply here? | Separate internal and external setup; the changeover reduction was an assumed percentage, not a measured result; what a real SMED study measures |
| What GMP issues touch your model? | Line clearance (211.130(e) for packaging and labeling; fill-area citation to verify), batch record review (211.192), Grade A fill zone and interventions (Annex 1), QA release; and why modeling doesn't replace validation |
| Why simulate instead of using a spreadsheet? | Variability, finite buffers, blocking, shared staff; averages hide queues |
| What would you do with real data? | Fit TTF/TTR from historian/MES, calibrate to measured OEE, run a holdout check |
| What are the limits? | Single line, liquid vials, no lyophilization, sub-lot discretization (tested), simplified tunnel, no deviations or absenteeism |
| How did you manage scope? | P0/P1/P2, cut ladder, pre-registered scenarios |
| Would you use this for a GxP decision? | No; decision-support only; a GxP-impacting tool would need computerized system validation (GAMP 5 approach) |

## LinkedIn project entry (T7.2.2)
Title: "Pharma Fill-Finish Digital Twin (Discrete-Event Simulation)". Two sentences + app link + repo link + the disclosure line.

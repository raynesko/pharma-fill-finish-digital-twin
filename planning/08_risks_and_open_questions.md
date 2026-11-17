# Risks and open questions

Ask the builder these at kickoff. None blocks work; the default is used until answered. Change a default by editing this table and the affected ticket.

| # | Question | Default assumption | Affects |
|---|---|---|---|
| 1 | Which drive/location is the project home? | `H:\resume_projects\` (the only large data drive available; no Google Drive mount was found). Move the folder if you meant a cloud drive | All |
| 2 | Is a public GitHub repo acceptable? | Yes, MIT license, no confidential data | T6.2.3, T7.1.3 |
| 3 | Dashboard tool: Streamlit or Power BI/Tableau? | Streamlit (free, Python-native, deployable). A Power BI view of exported results is optional and out of the plan | SE6 |
| 4 | Entity granularity | Sub-lot of 100 vials; decided in T3.1.2 | SE3 |
| 5 | Products and formats | 2 products x 2 vial formats, liquid only | T3.2.1 |
| 6 | Production horizon | One production week, 2 shifts x 8 h x 5 days | T4.1.3 |
| 7 | SME access for face validation | One practitioner or advisor; fallback structured self-review | T4.2.2 |
| 8 | Python version | 3.12 (installed) | T3.1.1 |
| 9 | Time budget | 9 h/week for 8 weeks; 6-week variant uses the minimum-viable plan | planning/03 |
| 10 | Include a sterility-test hold in QA release | Excluded by default (days to weeks would dominate lead time); batch-record review plus a short fixed release hold is modeled. Verify USP <71> details before changing | T3.2.4 |
| 11 | Changeover reduction levels | -25% and -50% as assumptions, not measured SMED outcomes | T5.1.1 |
| 12 | Tunnel behavior on stoppage | Fixed-residence element with backpressure; flagged for SME | T3.1.5 |

## Domain items I am not certain about (verify, do not guess)
- Realistic nominal speeds and MTBF/MTTR for each station (seed values are placeholders).
- A citable pharma OEE reference range and its definition.
- Typical AVI false-reject rates and re-inspection return fractions.
- How tunnel stoppage is handled in practice (vials in tunnel on stop).
- Whether serialization stops are better modeled as minor stoppages or as a separate loss.
- Exact current clause numbers and wording in EU GMP Annex 1 (2022) for interventions; cite section numbers only after reading them.

## Project risks
See charter section 9. Review at the weekly ritual (planning/03).

## Model findings to resolve before the baseline freeze (T4.2.1)
- **Campaign does not reliably fit one week (found 2026-11-16, T3.2.1).** With changeovers, quality and staffing on, 5 replications of the draft baseline finished at 104, 107, 110, 168 and 170 h. On the two long runs the last batch missed the Friday shift end and waited over the weekend, so the makespan is bimodal. A-039 frames the schedule as "one weekly campaign". Options: (a) keep it and report makespan as a weekend-spill probability, (b) report good vials per on-shift hour instead of makespan, (c) shorten the campaign to 5 batches. Decide in T4.2.1, before pre-registered scenarios run. RESULT (draft config, 5 reps, not frozen). Update after T3.2.6: in 30 replications (seed 20261116), **25 of 30 spilled over the weekend**. Makespan was 110-179 h. Good vials per PPT hour had a CV of about 4%, and good vials per calendar hour about 19%. This supports option (b): use the PPT-hour metric. **DECIDED 2026-11-17 by the project owner:** keep the 6-batch campaign (a), report spill as a finding, and make good vials per PPT hour primary (b). Recorded as amendments A1 and A2 in `docs/domain/scenario_hypotheses.md`.
- **Escapes are visible.** About 210-235 true defects per 600,000 vials reach the sink (missed by AVI at 0.85 detection, or unconfirmed on re-inspection). This follows from A-040/A-041 placeholders, not plant data; report it as a quality-risk metric only.

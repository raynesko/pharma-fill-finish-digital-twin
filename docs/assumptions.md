# Assumptions register

Ticket T2.1.2 · Every modeling assumption, structural and numeric. Numeric values point at a `param_id` in `data/raw/benchmark_sources.csv`; "J" means engineering judgment. **Sens = Y** means the assumption is perturbed in the sensitivity analysis (T5.2.2); the Y list here *is* the T5.2.2 parameter list. Add new assumptions at the bottom with the next ID; never renumber.

## Structural assumptions
| ID | Assumption | Rationale | Source | Plausible alternative | Sens |
|---|---|---|---|---|---|
| A-001 | Entities are sub-lots of N vials (default 100); quality is drawn per vial inside a sub-lot | Runtime about 115x faster than vial-level with output within N vials (measured) | ADR-001, B-034 | Vial-level entities | **Y** (N in 10/100/500) |
| A-002 | Breakdowns are operation-dependent: the failure clock runs only in `RUN` | Standard practice for machine failures; idle machines rarely fail by wear (Law, input modeling) | J | Calendar-time failures | N |
| A-003 | Interrupted work resumes where it stopped (preemptive-resume); no vials lost to a breakdown | Liquid vials in a jam are usually cleared and reinspected rather than scrapped en masse | J, VERIFY with SME | Partial scrap on breakdown | N |
| A-004 | Infinite upstream supply of empty vials, stoppers, caps and bulk product | Isolates line behavior from supply chain; supply failures are out of scope | Charter non-goals | Material shortages | N |
| A-005 | No operator absenteeism; staff are available whenever the shift calendar says so | Keeps staffing scenarios interpretable | J | Random absences | N |
| A-006 | Liquid-filled vials only; no lyophilization | Charter scope | Charter | Lyo cycle as batch bottleneck | N |
| A-007 | Depyrogenation tunnel is a fixed-residence delay element with finite capacity; a downstream stop applies backpressure to the washer and no vials are scrapped | Simplest representation that preserves latency and blocking | B-010, J, **VERIFY** (process_map SME Q1) | Scrap or re-process tunnel contents on long stops | N |
| A-008 | Filler and stoppering are one station with one failure clock | Integrated on vendor lines | B-004 | Separate stations | N |
| A-009 | External vial washing after capping is not modeled separately | Treated as part of the capper; open SME question | process_map Q8 | Separate machine with own failures | N |
| A-010 | Stations run at nominal rate while in `RUN`; reduced-speed loss is not modeled | Lack of data; listed as a limitation (glossary §4) | J | Speed-loss distribution | N |
| A-011 | No start-up scrap after changeovers | Lack of data; listed as a limitation | J | First-vial rejects per changeover | N |
| A-012 | Changeover type is determined by predecessor/successor batch and the station's scope: product-contact stations (filler) do product_change / format_change / same_product; packaging stations (capper, AVI, labeler, cartoner) do format_change or a same_product clearance; glass stations (washer, tunnel) do format_change only. Format+product change takes the product-change duration | Simple, testable lookup | B-017..B-019, J | Additive durations | N |
| A-013 | Each station starts its changeover as soon as it finishes the last sub-lot of the previous batch (rolling, overlapping changeovers across the line) | Reflects line practice of clearing station by station | J, VERIFY | Whole-line stop | N |
| A-014 | QA review never blocks the line; it only adds batch lead time | QA release is downstream of manufacturing (21 CFR 211.192) | Glossary D5 | Warehouse capacity limits | N |
| A-015 | Sterility/release testing hold is excluded by default | Would dominate lead time; not a line lever | B-029, open question 10 | 14-day hold enabled | N |
| A-016 | Minor stoppages are time intervals independent of entity boundaries, separate from breakdowns, cleared by the line operator without a mechanic | ADR-001 consequence; AZ classifies short stops as operator-cleared | B-014, B-015 | Treat as short breakdowns | **Y** (frequency) |
| A-017 | Rejects from AVI go to manual re-inspection; confirmed defects are scrapped, others return to the flow upstream of labeling | Common practice; return point is J | B-023..B-025, VERIFY | Rejects scrapped without re-inspection | N |
| A-018 | Repairs need a mechanic; changeovers need line operators; re-inspection needs an inspector; priority repair > changeover > re-inspection | Ensures staffing scenarios have mechanism | B-033, J | Shared generic pool | N |
| A-019 | Planned production: 2 shifts x 8 h x 5 days, 60 min breaks per shift (line stops for breaks) | Project default | B-031, B-032 | 24/7 with relief crews | N |
| A-020 | The simulation is terminating: start empty and clean, run a fixed weekly campaign to completion | Matches a weekly campaign question; no warm-up bias | Validation plan §2 | Steady-state with warm-up | N |
| A-021 | All inter-station buffers have equal capacity in vials | Lacking line-specific layout data | B-035 | Station-specific buffers | **Y** |
| A-022 | Line OEE uses the slowest nominal rate (filler) as ideal | Glossary D4 | J, SME | Constraint-based or scheduled-output based | N |

| A-023 | Production follows the shift calendar: on-shift windows of 2 x 8 h per day on 5 days, with one break per shift at mid-shift. Nothing runs, is repaired or changed over off-shift; machines resume where they stopped | Simplest calendar consistent with A-005 and A-019 | B-031, B-032 | Staggered breaks; repairs on nights | N |
| A-024 | Minor stoppages need no staff resource (cleared by the operator already on the line) | Keeps operator pool for changeovers | A-016, J | Operator resource required | N |
| A-025 | Manual re-inspection never rejects a good vial; vials it passes (false rejects and unconfirmed true defects) re-enter upstream of the labeler as a rework lot that is labeled and packed without a changeover, even if the labeler has already changed over to the next batch | Avoids modeling a separate reconciliation/pack-out step; slightly optimistic on packaging time | J, VERIFY with SME | Rework packed on a separate shift, or rejects scrapped without re-inspection | N |
| A-026 | Quality draws happen at the product-contact station (`changeover_scope: full`, the filler): fill-weight rejects are scrapped there, and true defects are created there and stay hidden until AVI | Fill is where product and container meet; defects from washing are folded into the incidence | B-022, B-026, J | Defects created at several stations | N |
| A-027 | With parallel units (SC-01), the same-product clearance is done only by the unit that finishes the batch; the other unit changes over only if format or product differs | Clearance is a line-level activity done once | J | Both units clear | N |

## Numeric assumptions (baseline modes; ranges in the CSV)
| ID | Parameter | Baseline | Source | Range | Sens |
|---|---|---|---|---|---|
| A-030 | Filler nominal rate | 240 vpm | B-003 | 60-500 | **Y** |
| A-031 | Washer / tunnel rate | 350 / 350 vpm | B-001, B-002 | 50-400 | N (well above filler) |
| A-032 | Capper / labeler / cartoner rate | 300 / 300 / 280 vpm | B-005, B-008, B-009 | see CSV | N (checked indirectly by bottleneck methods) |
| A-033 | AVI rate | 300 vpm | B-006 | 20-600 | **Y** |
| A-034 | Manual re-inspection rate | 5 vpm per inspector | B-007 | 3-6 | N (covered by staffing scenario) |
| A-035 | Breakdown time to failure: exponential, MTBF 4,800 min operating time, same for all stations | B-011 | 1,200-12,000 | **Y** |
| A-036 | Repair time: lognormal, mean 75 min, CV 0.8 | B-012, B-013 | 45-120 | **Y** |
| A-037 | Minor stoppage: exponential time between (mean 45 min run) and duration (mean 1.5 min) | B-014, B-015 | 15-120; 0.5-5 | **Y** (with A-016) |
| A-038 | Changeover durations: triangular(low, mode, high) per type: 45/90/150, 390/600/900, 90/180/300 min | B-017..B-019 | as listed | **Y** (all types scaled together) |
| A-039 | Batch size 100,000 vials; total weekly volume fixed across batch-size scenarios | B-036 | 20,000-200,000 | **Y** |
| A-040 | AVI true-defect incidence 0.2%, detection 0.85, false-reject 1% | B-022..B-024 | see CSV | **Y** (false-reject; defect incidence) |
| A-041 | Manual confirmation probability 0.95; fill-weight reject 0.1% | B-025, B-026 | see CSV | N |
| A-042 | QA review: shifted lognormal, mean 2,880 min, 2 reviewers | B-027, B-028 | 480-14,400 | **Y** (secondary metric only: lead time) |
| A-043 | Staffing: 4 operators, 1 mechanic, 2 inspectors | B-033 | +/-1 per role | N (scenario SC-03) |
| A-044 | Buffer capacity 2,000 vials between stations | B-035 | 1,000-5,000 | see A-021 |

## Distribution choices (justification for T2.1.3)
- **Exponential time to failure** (A-035): constant hazard is the usual default when only a mean is known (Law, *Simulation Modeling and Analysis*; Banks et al., *Discrete-Event System Simulation*). Weibull is preferred when wear-out data exist; none do here.
- **Lognormal repair time** (A-036): non-negative, right-skewed, commonly used for repair times in the same references.
- **Triangular changeover** (A-038): appropriate when only min/mode/max estimates exist (same references, "no data" input modeling).
- **Shifted lognormal QA review** (A-042): minimum review effort plus right-skewed backlog delays.
Citation details to verify before quoting: edition and section numbers of Law and Banks et al.

## Sensitivity list for T5.2.2 (derived from Sens = Y)
A-001 sub-lot N · A-016/A-037 minor stoppage frequency · A-021 buffer capacity · A-030 filler rate · A-033 AVI rate · A-035 MTBF · A-036 MTTR · A-038 changeover duration · A-039 batch size · A-040 false-reject rate and defect incidence · A-042 QA review (lead time only). That is 12 parameter runs (+/-20%; N uses levels 10/100/500).

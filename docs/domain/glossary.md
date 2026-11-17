# Glossary and KPI definitions (binding for code, tests, app and docs)

Ticket T1.1.2. Where a term has competing definitions in the literature, the choice below is a **modeling decision** for this project, labeled **DECISION**. The six-losses taxonomy follows Nakajima's *Introduction to TPM* (1988) as reported by secondary sources (vendor blogs; original not read, **VERIFY** before quoting). The 5-minute minor-stop cutoff sometimes quoted is a convention, not a standard, and is **not** used here: this model classifies stops by type (random breakdown vs minor stoppage), not by duration.

Time unit: minutes. Rate unit: vials per minute (vpm). Entities are sub-lots (default 100 vials) per the planned ADR-001; all metrics are reported in vials.

## 1. Time buckets (every station-minute falls in exactly one)
| Bucket | Meaning | Simulation state | OEE treatment |
|---|---|---|---|
| Calendar time | All minutes in the period (24 h x days) | n/a | Denominator of TEEP only |
| Planned stop | Breaks, planned maintenance, shift gaps | `PLANNED_STOP` | Excluded from planned production time |
| **Planned production time (PPT)** | Scheduled production minutes | all states below | Denominator of Availability |
| Breakdown | Random equipment failure and repair | `DOWN` | Availability loss |
| Changeover | Format/product change, cleaning, line clearance, setup and adjustment | `CHANGEOVER` | Availability loss (**DECISION D1**) |
| Wait for staff | Station idle because a required operator or mechanic is unavailable | `WAIT_STAFF` | Availability loss (**DECISION D2**) |
| **Operating time** | PPT minus the three availability losses above | the four states below | Denominator of Performance |
| Minor stoppage | Short, frequent stops (jams, sensor trips, adjustments) | `MINOR_STOP` | Performance loss |
| Starved | Running-capable but no input | `STARVED` | Performance loss (**D3**) |
| Blocked | Running-capable but output buffer full | `BLOCKED` | Performance loss (**D3**) |
| Run | Processing at nominal rate | `RUN` | Productive time |

**D1 Changeover is an availability loss.** It is a setup-and-adjustment loss in the six big losses, and it is the lever SMED attacks. Alternative treatments (counting it as planned stop, so it vanishes from OEE) would hide exactly the lever the scenario study varies.
**D2 Wait-for-staff is an availability loss**, because the station cannot run for want of a resource it needs. It is also reported as its own category so staffing scenarios stay interpretable.
**D3 Starvation and blocking count against Performance at station level**, which matches how a station's output relative to its nominal rate is measured. They are reported as separate loss categories in the Pareto, never merged into a single "performance" slice, so a reader can tell flow losses from machine losses. They are **not** the station's own fault; the bottleneck methods (T5.2.3) use them to find the constraint.

## 2. OEE
- **Availability A** = Operating time / PPT.
- **Performance P** = Actual output (vials processed) / (Operating time x nominal rate). Captures minor stoppages, starvation, blocking and reduced speed.
- **Quality Q** = Good vials / vials processed by that station.
- **OEE** = A x P x Q = Good vials / (PPT x nominal rate).

The identity OEE = good vials / (PPT x nominal rate) is used as a unit-test invariant.

### Worked example (reused as a test fixture in T3.2.5)
One station, nominal rate 200 vpm, one 8 h shift.
| Item | Minutes |
|---|---|
| PPT | 480 |
| Breakdown | 30 |
| Changeover | 40 |
| Wait for staff | 10 |
| **Operating time** | **400** |
| Minor stoppage | 5 |
| Starved | 20 |
| Blocked | 15 |
| Run | 360 |

- A = 400 / 480 = 0.83333
- Output = 360 x 200 = 72,000 vials. P = 72,000 / (400 x 200 = 80,000) = 0.90000
- Rejects 2% of 72,000 = 1,440, so good = 70,560. Q = 70,560 / 72,000 = 0.98000
- **OEE = 0.83333 x 0.90 x 0.98 = 0.735** = 70,560 / (480 x 200 = 96,000) ✓
- Good vials per hour = 70,560 / 8 = **8,820**
- Utilization = Run / PPT = 360 / 480 = **0.75**

Loss Pareto for this example, as % of PPT: changeover 8.3, breakdown 6.25, starved 4.17, blocked 3.13, wait-staff 2.08, minor stoppage 1.04, quality 1.5 equivalent (the 1,440 rejected vials = 7.2 min of run at 200 vpm, 1.5% of PPT).
Check: 8.33+6.25+4.17+3.13+2.08+1.04+1.5 = 26.5% = 1 - 0.735 ✓.

### Line-level OEE (**DECISION D4**)
- **Line OEE** = Good vials packed / (PPT x nominal rate of the slowest-nominal-rate station), the "reference station".
- Q_line = good vials packed / vials started at the line entry. A_line = A of the reference station. P_line is the residual so that A x P x Q equals Line OEE exactly; it therefore includes flow losses caused by other stations. Using the slowest nominal rate as ideal means Line OEE cannot exceed 1 and answers "how much of the line's theoretical best did we achieve".
- Flagged for SME confirmation: plants differ (some use constraint-station OEE, some a ratio of packaged to scheduled output). Show the definition next to every line OEE number.

## 3. Other KPIs
| Term | Definition |
|---|---|
| **TEEP** (Total Effective Equipment Performance) | OEE x (PPT / calendar time). Example above with calendar day 1,440 min: 0.735 x (480/1440) = **0.245** |
| **Loading (schedule utilization)** | PPT / calendar time |
| **Utilization** (station) | Run time / PPT. Differs from A and P. Example: 0.75 |
| **Throughput** | Good vials per hour out of the line (primary scenario metric) |
| **Cycle time** (batch) | Batch start on the line to last vial packaged |
| **Lead time** (batch) | Batch start to QA release = cycle time + QA wait and hold. Example: batch of 10,000 vials starts 08:00, packaging completes 14:00 (cycle 6 h), QA release 24 h later (lead time 30 h) |
| **WIP** | Vials (or sub-lots) inside the line between entry and packaging |
| **Queue length / queue time** (buffer) | Time-weighted mean number in, and mean time spent in, a buffer. **Little's Law**: L = lambda x W. Example: 3 sub-lots/min x 4 min = 12 sub-lots |
| **MTBF / MTTR** | Mean operating time between failures / mean repair time. Inherent availability = MTBF / (MTBF + MTTR); example 240 / 260 = **0.9231**. Operation-dependent: failure clock runs only in `RUN` |
| **Minor stoppage** | Short, frequent stoppage self-cleared or cleared by the operator without a repair crew; modeled with its own distribution, separate from breakdowns |
| **Starvation / blocking** | No input available / output buffer full (see D3) |
| **Changeover** | Everything between the last good vial of batch A and first good vial of batch B on a station: cleaning, part change, line clearance, adjustments, first-article checks. Three types: same-product, product change, format change |
| **Line clearance** | A verification step inside a changeover: confirming earlier product, materials and labels are removed and documenting it. For packaging and labeling it is required by 21 CFR 211.130(e); fill-area citation is **VERIFY** (see process_map.md) |
| **SMED** (Single-Minute Exchange of Die) | Shingo's method to cut changeover time: separate internal setup (machine stopped) from external (machine running), convert internal to external, streamline both. A scenario reduction percentage is an **assumption**, not a measured SMED result |
| **QA hold / batch disposition** | Time between completing manufacturing and the quality unit's release decision, including batch-record review (21 CFR 211.192) and any release testing. **DECISION D5:** excluded from equipment OEE; reported as lead time |
| **Bottleneck / constraint (Theory of Constraints)** | The resource that limits system throughput. Goldratt's five focusing steps: identify, exploit, subordinate, elevate, repeat. Improving a non-constraint adds WIP, not output. Here the constraint is an output of the model, found by several methods; with random failures it can move |
| **Common random numbers (CRN)** | Using the same random streams across scenarios so differences are due to the change, not noise |
| **Terminating simulation** | One whose natural end is an event (all batches packed); no warm-up needed if the real system also starts clean |

## 4. Six big losses mapped to this model
| Six big loss | OEE factor | Model category (ledger) |
|---|---|---|
| Equipment failure | Availability | `DOWN` |
| Setup and adjustment | Availability | `CHANGEOVER` (and `WAIT_STAFF` as a resource loss, D2) |
| Idling and minor stoppages | Performance | `MINOR_STOP`, `STARVED`, `BLOCKED` |
| Reduced speed | Performance | Reserved: not modeled in v1.0 (stations run at nominal rate while `RUN`); listed as a limitation |
| Process defects | Quality | AVI true rejects, fill-weight rejects |
| Reduced yield / start-up | Quality | Not modeled in v1.0 (no start-up scrap); false rejects counted under defects |

## 5. Items for SME confirmation
1. Line-level OEE definition (D4).
2. Whether starvation and blocking are better excluded from station Performance (some plants do, calling them "external" losses).
3. Whether wait-for-staff belongs in Availability (D2) or in a separate "organizational" loss.

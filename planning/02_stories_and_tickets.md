# Stories and tickets (generated from planning/tickets/; edit the ticket files, not this)

## SE1 - Domain Research & Problem Framing

**[S1.1] Understand the aseptic fill-finish process and KPI vocabulary**
- Type: Story
- Sub-epic: SE1 - Domain Research & Problem Framing
- As a: process-improvement analyst
- I want: a cited, correct picture of the vial fill-finish flow and a precise KPI glossary
- So that: the model structure and OEE definitions will survive scrutiny from a manufacturing engineer
- Description: Foundation story: process map, GMP control points, and unambiguous metric definitions.
- Acceptance criteria:
  - [ ] Process map and glossary reviewed against sources
  - [ ] Open questions for an SME are listed
- Dependencies: none
- Estimate: rollup of child tickets (computed by tools/build_index.py)
- Priority: inherits highest child priority
- Deliverable/artifact: all child deliverables

_Story rollup: 4 h_

**[T1.1.1] Aseptic fill-finish process walk-through**
- Type: Spike
- Sub-epic: SE1 - Domain Research & Problem Framing
- Story: S1.1
- Description: Document the liquid-vial aseptic line end to end: vial washing, depyrogenation tunnel, filling, stoppering, capping/crimping, inspection (automated + manual), labeling, packaging/serialization, and QA review/release. For each step record purpose, equipment type, flow type (continuous, intermittent, batch), typical rate range, dominant downtime causes and GMP control points (e.g., Grade A fill zone under EU GMP Annex 1 2022, line clearance (21 CFR 211.130(e) applies to packaging and labeling; fill-area citation to verify), in-process checks). Explicitly exclude lyophilization, formulation and terminal sterilization.
- Acceptance criteria:
  - [x] All 9 steps documented with purpose, equipment, flow type and at least one GMP control point
  - [x] At least 8 distinct citable sources (FDA 2004 aseptic processing guidance, EU GMP Annex 1, 21 CFR 210/211, ISPE Baseline Guide Vol. 3, vendor datasheets, peer-reviewed papers)
  - [x] Mermaid flow diagram renders on GitHub
  - [x] Uncertain-items list with at least 3 questions flagged for an SME (not guessed)
  - [x] Out-of-scope list is explicit (lyophilization, formulation, media fills, terminal sterilization)
- Dependencies: none
- Estimate: 3 h (M)
- Priority: P0
- Deliverable/artifact: docs/domain/process_map.md (+ Mermaid diagram), docs/domain/sources.md

**[T1.1.2] Glossary and KPI definitions**
- Type: Task
- Sub-epic: SE1 - Domain Research & Problem Framing
- Story: S1.1
- Description: Define every metric the project reports, with formulas and a worked numeric example, and make two contested modeling choices explicit: how changeover is classified in OEE, and where QA hold time lives.
- Acceptance criteria:
  - [x] Defines OEE (Availability, Performance, Quality) with the time bucket for each, TEEP, utilization, throughput, cycle time vs lead time, WIP, changeover vs line clearance, SMED, MTBF/MTTR, starvation vs blocking, QA hold / batch disposition, bottleneck / Theory of Constraints, six big losses
  - [x] Decision recorded: changeover counted as an availability loss (setup and adjustment); rationale and source cited
  - [x] Decision recorded: QA hold excluded from equipment OEE and reported as batch lead time
  - [x] Each formula has a worked numeric example that T3.2.5 will reuse as a test fixture
- Dependencies: none
- Estimate: 1 h (S)
- Priority: P0
- Deliverable/artifact: docs/domain/glossary.md

---

**[S1.2] Frame the decisions the simulation must inform**
- Type: Story
- Sub-epic: SE1 - Domain Research & Problem Framing
- As a: continuous-improvement engineer
- I want: falsifiable scenario hypotheses written before any model code
- So that: the scenario study answers real decisions instead of being a fishing expedition
- Description: Decision framing and pre-registration of hypotheses.
- Acceptance criteria:
  - [ ] Hypotheses written before scenario runs
  - [ ] No bottleneck pre-committed
- Dependencies: none
- Estimate: rollup of child tickets (computed by tools/build_index.py)
- Priority: inherits highest child priority
- Deliverable/artifact: all child deliverables

_Story rollup: 1.5 h_

**[T1.1.3] Scenario hypotheses and decision questions**
- Type: Task
- Sub-epic: SE1 - Domain Research & Problem Framing
- Story: S1.2
- Description: Before any model code exists, write falsifiable hypotheses for the required scenarios (add inspection station, change batch size, change staffing, reduce changeover time) plus one combination. This is the pre-registration that guards against post-hoc storytelling.
- Acceptance criteria:
  - [x] At least 5 scenarios including the 4 required levers
  - [x] Each has: decision-maker question, mechanism (Theory of Constraints reasoning), expected direction labeled HYPOTHESIS, primary metric, and what result would refute it
  - [x] States explicitly that no bottleneck is pre-committed; it is an output of the model
  - [x] File committed before the first scenario run (git history shows the order)
- Dependencies: T1.1.1, T1.1.2
- Estimate: 1.5 h (S)
- Priority: P0
- Deliverable/artifact: docs/domain/scenario_hypotheses.md

---

## SE2 - Parameterization, Data & Assumptions

**[S2.1] Build a cited, validated parameter set**
- Type: Story
- Sub-epic: SE2 - Parameterization, Data & Assumptions
- As a: modeler
- I want: every model input traceable to a source or an explicit judgment tag
- So that: a reviewer can audit why each number is what it is, and sensitivity analysis knows where to look
- Description: Benchmark sourcing, assumptions register, distribution derivation, and a validated config schema.
- Acceptance criteria:
  - [ ] No orphan parameters: each config value maps to a benchmark row or a judgment tag
  - [ ] Config schema rejects invalid input
- Dependencies: none
- Estimate: rollup of child tickets (computed by tools/build_index.py)
- Priority: inherits highest child priority
- Deliverable/artifact: all child deliverables

_Story rollup: 8 h_

**[T2.1.1] Benchmark sourcing for rates, reliability, changeovers and quality**
- Type: Spike
- Sub-epic: SE2 - Parameterization, Data & Assumptions
- Story: S2.1
- Description: Find a published or vendor value (or range) for every parameter family: nominal speeds per station, MTBF/MTTR or availability, minor-stoppage frequency, changeover and cleaning durations, AVI defect detection and false-reject rates, manual inspection rates, QA review durations, shift patterns, and published OEE reference ranges for pharma/packaging. Seed values in the charter are placeholders to be replaced here.
- Acceptance criteria:
  - [x] CSV columns: param_id, description, value_low, value_mode, value_high, unit, source_title, url_or_doc, retrieved_date, confidence (H/M/L), notes
  - [x] At least 25 rows covering all 8 stations plus changeover, quality and QA release
  - [x] Every row has a source OR the tag engineering_judgment with a written reason
  - [x] At least one sourced pharma/packaging OEE reference range, with the definition caveats noted (OEE definitions differ between sources)
  - [x] All units convertible to vials/min and minutes with no ambiguity
- Dependencies: T1.1.1
- Estimate: 3 h (M)
- Priority: P0
- Deliverable/artifact: data/raw/benchmark_sources.csv

**[T2.1.2] Assumptions register**
- Type: Task
- Sub-epic: SE2 - Parameterization, Data & Assumptions
- Story: S2.1
- Description: Single table of every modeling assumption, structural and numeric. This is the document a reviewer reads to decide whether to trust the model.
- Acceptance criteria:
  - [x] At least 20 assumptions with ID A-###, statement, rationale, source param_id or judgment, plausible range, sensitivity flag (Y/N)
  - [x] Structural assumptions included: entity granularity, failures only while running, no absenteeism, liquid vials only, infinite upstream supply, tunnel simplification
  - [x] Renders as a readable table on GitHub
  - [x] Every Y-flagged assumption has a matching planned sensitivity run in T5.2.2
- Dependencies: T2.1.1
- Estimate: 1 h (S)
- Priority: P0
- Deliverable/artifact: docs/assumptions.md

**[T2.1.3] Distributions and parameter derivation**
- Type: Task
- Sub-epic: SE2 - Parameterization, Data & Assumptions
- Story: S2.1
- Description: Convert benchmark summaries into sampling distributions: time-to-failure exponential or Weibull from MTBF, repair time lognormal from mean and CV, changeover triangular or lognormal from low/mode/high, QA hold shifted lognormal. Justify each choice with simulation-input-modeling guidance (Law; Banks et al.).
- Acceptance criteria:
  - [x] Functions for each conversion with docstrings stating units
  - [x] pytest: 100,000 draws reproduce the target mean within 1% (target) and CV within 3% (target)
  - [x] Each distribution choice cited in docs/assumptions.md
  - [x] All sampling goes through numpy Generator seeded from SeedSequence (no global RNG)
- Dependencies: T2.1.1, T2.1.2
- Estimate: 2 h (M)
- Priority: P0
- Deliverable/artifact: src/ffdt/params.py, tests/unit/test_params.py

**[T2.1.4] Config schema and baseline_line.yaml**
- Type: Task
- Sub-epic: SE2 - Parameterization, Data & Assumptions
- Story: S2.1
- Description: A pydantic schema describing the line (stations, buffers, products, formats, shifts, staffing, quality, QA) and the first baseline YAML. Unit suffixes in field names (_min, _vpm, _vials).
- Acceptance criteria:
  - [x] Schema validates ranges (rates > 0, probabilities in [0,1], buffer >= 1)
  - [x] Baseline YAML defines all 8 stations, buffers, at least 2 products x 2 vial formats, shifts, staffing
  - [x] Every value carries a comment # src: <param_id> that exists in benchmark_sources.csv (checked by tools/check_param_ids.py)
  - [x] At least 5 negative tests produce clear error messages
- Dependencies: T2.1.3, T3.1.2
- Estimate: 2 h (M)
- Priority: P0
- Deliverable/artifact: src/ffdt/config.py, configs/baseline_line.yaml, tests/unit/test_config.py, tools/check_param_ids.py

---

## SE3 - Simulation Model Build

**[S3.1] Core line simulation with stochastic downtime**
- Type: Story
- Sub-epic: SE3 - Simulation Model Build
- As a: modeler
- I want: a configurable SimPy line with finite buffers, failures and a state log
- So that: throughput, blocking and starvation emerge from the mechanics, not from hard-coded answers
- Description: Machine abstraction, failures, line assembly, scaffolding and the granularity decision.
- Acceptance criteria:
  - [ ] Baseline week simulates without deadlock
  - [ ] Vial conservation holds
- Dependencies: none
- Estimate: rollup of child tickets (computed by tools/build_index.py)
- Priority: inherits highest child priority
- Deliverable/artifact: all child deliverables

_Story rollup: 10 h_

**[T3.1.1] Project scaffold, tooling and CI**
- Type: Task
- Sub-epic: SE3 - Simulation Model Build
- Story: S3.1
- Description: Create the package skeleton per docs/repo structure. Pin exact versions at scaffold time with pip freeze after install; do not guess version numbers.
- Acceptance criteria:
  - [x] Fresh venv: pip install -r requirements-dev.txt succeeds
  - [x] make test passes with one placeholder test; make lint passes (ruff) [verified via python tasks.py, no make on this Windows machine]
  - [x] CI workflow runs pytest on push (or a documented local equivalent if no GitHub remote)
  - [x] Folder layout matches planning/05_repo_structure.md
- Dependencies: none
- Estimate: 1 h (S)
- Priority: P0
- Deliverable/artifact: pyproject.toml, requirements.txt, requirements-dev.txt, Makefile, .gitignore, LICENSE, .github/workflows/ci.yml, src/ffdt/__init__.py, tests/

**[T3.1.2] ADR: entity granularity and time unit**
- Type: Spike
- Sub-epic: SE3 - Simulation Model Build
- Story: S3.1
- Description: Compare vial-level entities against sub-lot entities (N vials per entity, default N=100) on a one-machine prototype running a one-week campaign at the nominal filler rate. Measure SimPy runtime and note accuracy trade-offs. Simulation time unit: minutes.
- Acceptance criteria:
  - [x] Runtime measured and recorded for both options
  - [x] Decision recorded in ADR format (context, decision, consequences) including the discretization effect on AVI rejects and blocking
  - [x] Target: one baseline replication runs in under 10 s (target)
  - [x] Sub-lot size N is a config parameter and appears in the T5.2.2 sensitivity list
- Dependencies: T3.1.1
- Estimate: 1 h (S)
- Priority: P0
- Deliverable/artifact: docs/adr/adr_001_entity_granularity.md

**[T3.1.3] Machine process with finite buffers and state log**
- Type: Task
- Sub-epic: SE3 - Simulation Model Build
- Story: S3.1
- Description: Reusable Machine class: takes sub-lots from an input Store, processes at its nominal rate, puts into an output Store (blocking when full), and records contiguous state intervals: RUN, STARVED, BLOCKED, DOWN, MINOR_STOP, CHANGEOVER, PLANNED_STOP, WAIT_STAFF (names fixed by docs/domain/glossary.md).
- Acceptance criteria:
  - [x] State intervals are contiguous, non-overlapping and sum to simulated time (test)
  - [x] Buffer occupancy never exceeds capacity (test)
  - [x] Two-machine line without failures: throughput equals min(rate) within 0.1% (test)
  - [x] Starvation and blocking classified correctly in a constructed case (test)
  - [x] Docstring states time unit and rate unit
- Dependencies: T3.1.2, T2.1.4
- Estimate: 3 h (M)
- Priority: P0
- Deliverable/artifact: src/ffdt/sim/machine.py, tests/unit/test_machine.py

**[T3.1.4] Stochastic failures and repairs**
- Type: Task
- Sub-epic: SE3 - Simulation Model Build
- Story: S3.1
- Description: Operation-dependent failures (the failure clock advances only while RUN), repair-time draws, and separate minor stoppages (short, frequent). Repair interrupts the job and resumes the remaining work (preemptive-resume).
- Acceptance criteria:
  - [x] Isolated machine long-run availability is within 2% (target) of MTBF/(MTBF+MTTR) (test)
  - [x] Interrupted work resumes with remaining time; no vial lost or duplicated (test)
  - [x] Breakdowns and minor stoppages tracked as separate loss categories
  - [x] Same seed gives identical event log (test)
- Dependencies: T3.1.3, T2.1.3
- Estimate: 2 h (M)
- Priority: P0
- Deliverable/artifact: src/ffdt/sim/failures.py, tests/unit/test_failures.py

**[T3.1.5] Line assembly from configuration**
- Type: Task
- Sub-epic: SE3 - Simulation Model Build
- Story: S3.1
- Description: Wire washer, depyrogenation tunnel, filler, stopper/capper, automated visual inspection, labeler, cartoner/serializer with finite buffers. Tunnel simplification: fixed residence-time element with backpressure on the washer; document the effect and flag for SME confirmation.
- Acceptance criteria:
  - [x] Line is built purely from YAML; no station names hard-coded in logic
  - [x] Vial conservation: started = packed + scrap + WIP at all times (test)
  - [x] Baseline one-week simulation completes without deadlock
  - [x] Tunnel simplification recorded in the assumptions register
  - [x] Smoke notebook plots per-station state timeline
- Dependencies: T3.1.4
- Estimate: 3 h (M)
- Priority: P0
- Deliverable/artifact: src/ffdt/sim/line.py, notebooks/01_smoke_run.ipynb

---

**[S3.2] Production planning, people, quality and metrics**
- Type: Story
- Sub-epic: SE3 - Simulation Model Build
- As a: modeler
- I want: batches, changeovers, staffing, QA release, quality loss and an OEE metrics layer
- So that: the model reproduces the operational levers the scenario study needs to pull
- Description: Everything that makes the line behave like a GMP line rather than a generic conveyor.
- Acceptance criteria:
  - [ ] All four required scenario levers exist as config parameters
  - [ ] Metrics computed solely from the state ledger
- Dependencies: none
- Estimate: rollup of child tickets (computed by tools/build_index.py)
- Priority: inherits highest child priority
- Deliverable/artifact: all child deliverables

_Story rollup: 11.5 h_

**[T3.2.1] Batch generator, campaign schedule and changeovers**
- Type: Task
- Sub-epic: SE3 - Simulation Model Build
- Story: S3.2
- Description: Seeded production schedule over at least 2 products and 2 vial formats with batch sizes in vials. Changeover type is chosen from the predecessor/successor pair: same-product line clearance, product change with full clean, format change with change parts. Each type has its own duration distribution and affected stations; line clearance (21 CFR 211.130(e) for packaging and labeling; fill-area citation per docs/domain/process_map.md).
- Acceptance criteria:
  - [x] Fixed-sequence mode exists for verification
  - [x] Changeover type lookup is tested over the full predecessor/successor matrix
  - [x] CHANGEOVER state is logged on each affected station
  - [x] Total vials started equals the sum of batch sizes (test)
  - [x] Batch record table: batch_id, product, format, size, start, end, yield
- Dependencies: T3.1.5
- Estimate: 3 h (M)
- Priority: P0
- Deliverable/artifact: src/ffdt/sim/batches.py, tests/unit/test_batches.py

**[T3.2.2] Quality loss model (AVI and in-process rejects)**
- Type: Task
- Sub-epic: SE3 - Simulation Model Build
- Story: S3.2
- Description: AVI with true-defect rate, detection probability and false-reject rate; rejects go to a manual re-inspection pool (see T3.2.3) with a return fraction, or to scrap. Fill-weight in-process reject as a second quality loss.
- Acceptance criteria:
  - [x] Yield equals good vials over vials started; reconciles with conservation test
  - [x] Rejects attributed by cause in a quality-loss ledger
  - [x] With defect rate 0 and false-reject 0, Quality = 100% (test)
  - [x] Sampled reject fraction is within binomial 95% bounds of the configured rate (test)
  - [x] Parameters trace to benchmark rows
- Dependencies: T3.1.5
- Estimate: 1 h (S)
- Priority: P0
- Deliverable/artifact: src/ffdt/sim/quality.py, tests/unit/test_quality.py

**[T3.2.3] Staffing and operator resources**
- Type: Task
- Sub-epic: SE3 - Simulation Model Build
- Story: S3.2
- Description: Operators as prioritized SimPy resource pools by role (line operator, mechanic, inspector). Changeovers, repairs and manual re-inspection require staff; shift calendar produces PLANNED_STOP for breaks. Required for the staffing scenario.
- Acceptance criteria:
  - [x] With staff = 0 in a role, dependent activities do not start (test)
  - [x] Wait-for-staff time is logged as its own loss category (WAIT_STAFF)
  - [x] Priority order repair > changeover > re-inspection is documented and tested
  - [x] Staffing level is overridable by scenario YAML
- Dependencies: T3.2.1, T3.2.2
- Estimate: 2 h (M)
- Priority: P0
- Deliverable/artifact: src/ffdt/sim/staffing.py, tests/unit/test_staffing.py

**[T3.2.4] QA hold and batch release**
- Type: Task
- Sub-epic: SE3 - Simulation Model Build
- Story: S3.2
- Description: After a batch is fully packaged it enters a QA queue: batch-record review (21 CFR 211.192) by finite reviewers plus a fixed release-testing hold. Output is batch lead time and release time. It never blocks the line. Verify the sterility test incubation period (commonly cited as 14 days in USP <71>) before using it, or exclude it and say so.
- Acceptance criteria:
  - [x] Batch lead time (start to release) recorded per batch
  - [x] QA hold distribution traces to benchmark rows or a judgment tag
  - [x] Toggling QA hold leaves equipment OEE identical under common random numbers (test)
  - [x] QA reviewer queue time reported
- Dependencies: T3.2.1
- Estimate: 1 h (S)
- Priority: P0
- Deliverable/artifact: src/ffdt/sim/qa_release.py, tests/unit/test_qa_release.py

**[T3.2.5] Metrics collector and OEE layer**
- Type: Task
- Sub-epic: SE3 - Simulation Model Build
- Story: S3.2
- Description: Turn the state ledger into tidy DataFrames and compute per-station and line OEE (A, P, Q), utilization, good-vials-per-hour, time-weighted queue length and time in queue, WIP, batch cycle time. Computed only from the ledger, never from simulation internals. Calendar overlay (found in T3.1.5 smoke run): the sim only records PLANNED_STOP for a station that is mid-activity at shift end; STARVED, BLOCKED and WAIT_STAFF intervals that overlap off-shift time must be split and the off-shift part reclassified as PLANNED_STOP, so PPT is identical for every station.
- Acceptance criteria:
  - [x] OEE reproduces the glossary worked example exactly (test using expected values)
  - [x] Loss categories map to the six big losses
  - [x] Time-weighted queue length available for Little's Law check
  - [x] Output schema documented in docs/metrics_schema.md
  - [x] Metrics module imports nothing from ffdt.sim
  - [x] After the calendar overlay, every station's PLANNED_STOP minutes are equal within a run (test)
- Dependencies: T3.2.1, T3.2.2, T1.1.2
- Estimate: 3 h (M)
- Priority: P0
- Deliverable/artifact: src/ffdt/metrics/ledger.py, src/ffdt/metrics/oee.py, tests/unit/test_oee.py

**[T3.2.6] Experiment runner with seeded replications**
- Type: Task
- Sub-epic: SE3 - Simulation Model Build
- Story: S3.2
- Description: run(config, n_reps, seed) returning per-replication metrics. Independent random streams per station via SeedSequence.spawn so unchanged stations draw identical numbers across scenarios (common random numbers).
- Acceptance criteria:
  - [x] Parallel (joblib) results equal serial results (test)
  - [x] Results written to parquet with config hash and git SHA in metadata
  - [x] 30 baseline replications finish in under 2 minutes on a student laptop (target)
  - [x] Changing one station's parameter leaves other stations' random streams unchanged (test)
- Dependencies: T3.2.5
- Estimate: 1.5 h (S)
- Priority: P0
- Deliverable/artifact: src/ffdt/experiments/runner.py, tests/unit/test_runner.py

---

## SE4 - Verification, Validation & Baseline

**[S4.1] Verify the model is built right**
- Type: Story
- Sub-epic: SE4 - Verification, Validation & Baseline
- As a: reviewer
- I want: automated invariant and analytical tests plus a defensible run-length design
- So that: I can trust the simulator is free of logic errors before looking at results
- Description: Unit, invariant and closed-form checks; warm-up and replication count.
- Acceptance criteria:
  - [ ] All verification tests pass in CI
  - [ ] Replication count justified by CI half-width
- Dependencies: none
- Estimate: rollup of child tickets (computed by tools/build_index.py)
- Priority: inherits highest child priority
- Deliverable/artifact: all child deliverables

_Story rollup: 5 h_

**[T4.1.1] Invariant and unit test suite**
- Type: Task
- Sub-epic: SE4 - Verification, Validation & Baseline
- Story: S4.1
- Description: Property-style checks that must hold for any valid configuration.
- Acceptance criteria:
  - [x] Vial conservation holds across at least 20 random configs
  - [x] State-time sums equal horizon per station
  - [x] No-failure throughput equals bottleneck rate within 0.5%
  - [x] Empty-schedule and single-batch edge cases pass
  - [x] Line coverage of src/ffdt/sim at least 90% (target); suite runs in under 60 s
- Dependencies: T3.2.5
- Estimate: 2 h (M)
- Priority: P0
- Deliverable/artifact: tests/verification/test_invariants.py

**[T4.1.2] Analytical cross-checks**
- Type: Task
- Sub-epic: SE4 - Verification, Validation & Baseline
- Story: S4.1
- Description: Compare the simulator, configured as simple systems, with closed forms: M/M/1 queue wait Wq = lambda / (mu (mu - lambda)), M/M/1/K blocking probability, availability formula, and Little's Law on each buffer.
- Acceptance criteria:
  - [x] Simulated M/M/1 mean queue wait within 2% (target) of theory over at least 30 replications
  - [x] M/M/1/K blocking probability inside the 95% CI
  - [x] Little's Law relative error under 1% on every buffer
  - [x] Theory vs simulation vs CI table in docs/verification.md
- Dependencies: T3.2.6
- Estimate: 1.5 h (S)
- Priority: P0
- Deliverable/artifact: tests/verification/test_analytic.py, docs/verification.md

**[T4.1.3] Run length, warm-up and replication count**
- Type: Task
- Sub-epic: SE4 - Verification, Validation & Baseline
- Story: S4.1
- Description: Primary mode is a terminating simulation of a fixed campaign (start empty and clean, run until all batches are packed). Use a steady-state mode with Welch's method only for verification. Choose replications so the 95% CI half-width is at most 2% of the mean for OEE and throughput.
- Acceptance criteria:
  - [x] Terminating vs steady-state decision documented with rationale
  - [x] Welch plot produced for the steady-state verification model
  - [x] Replication count n chosen from a pilot of at least 10 runs using t-based half-width
  - [x] n written to configs/experiment.yaml and used by all later runs
- Dependencies: T3.2.6, T4.1.1
- Estimate: 1.5 h (S)
- Priority: P0
- Deliverable/artifact: notebooks/04_warmup_reps.ipynb, section in docs/verification.md

---

**[S4.2] Freeze a baseline and test face validity**
- Type: Story
- Sub-epic: SE4 - Verification, Validation & Baseline
- As a: reviewer
- I want: a frozen, documented as-is baseline with a plausibility review
- So that: all scenario results are measured against one unambiguous reference
- Description: Baseline definition, SME/advisor review, baseline results report.
- Acceptance criteria:
  - [ ] Baseline tagged and hashed
  - [ ] Validation limits stated honestly
- Dependencies: none
- Estimate: rollup of child tickets (computed by tools/build_index.py)
- Priority: inherits highest child priority
- Deliverable/artifact: all child deliverables

_Story rollup: 4.5 h_

**[T4.2.1] Freeze baseline v1.0**
- Type: Task
- Sub-epic: SE4 - Verification, Validation & Baseline
- Story: S4.2
- Description: Define the as-is line precisely and freeze it. Any later change to baseline parameters requires a v1.1 with a changelog.
- Acceptance criteria:
  - [x] Git tag baseline-v1.0 created
  - [x] Config hash recorded in docs/baseline_definition.md
  - [x] One page states products, schedule, staffing, OEE definition, and what baseline means (as-is configured line, not a real plant)
  - [x] All verification tests pass at the tag
- Dependencies: T4.1.1, T4.1.2, T4.1.3
- Estimate: 0.5 h (S)
- Priority: P0
- Deliverable/artifact: docs/baseline_definition.md, git tag baseline-v1.0

**[T4.2.2] Face validation with a practitioner**
- Type: Task
- Sub-epic: SE4 - Verification, Validation & Baseline
- Story: S4.2
- Description: 30-minute structured walk-through with at least one practitioner (alumnus, professor, ISPE student chapter, LinkedIn contact in NJ pharma). Fallback: faculty advisor plus a structured self-review against sources. Start outreach in week 2 so the meeting lands by week 8. Keep any shared plant details out of the log.
- Acceptance criteria:
  - [ ] Reviewer role and date logged (no confidential information)
  - [ ] At least 5 checklist items judged: flow, rates, downtime magnitude, changeover, QA hold
  - [ ] At least 1 change made or rejected with a reason
  - [ ] Baseline OEE compared with the sourced reference band from T2.1.1 and any gap explained
  - [ ] Explicit statement that validation is limited to face validity because no real plant data was used
- Dependencies: T4.2.1
- Estimate: 2 h (M)
- Priority: P1
- Deliverable/artifact: docs/validation/face_validation_log.md

**[T4.2.3] Baseline results report**
- Type: Task
- Sub-epic: SE4 - Verification, Validation & Baseline
- Story: S4.2
- Description: Report baseline performance with uncertainty and the first evidence about the constraint.
- Acceptance criteria:
  - [ ] OEE A/P/Q per station and line with 95% CI (t-based, n from T4.1.3)
  - [ ] Loss Pareto using six-big-losses categories
  - [ ] State-time stacked bar per station
  - [ ] Preliminary bottleneck evidence (utilization, blocking, starvation) without conclusion language
  - [ ] Every figure labeled simulated and benchmark-parameterized; numbers exported to results_baseline.json
- Dependencies: T4.2.1
- Estimate: 2 h (M)
- Priority: P0
- Deliverable/artifact: notebooks/05_baseline_report.ipynb, reports/baseline.md, reports/results_baseline.json

---

## SE5 - Scenario & Bottleneck Study

**[S5.1] Design and execute the scenario experiments**
- Type: Story
- Sub-epic: SE5 - Scenario & Bottleneck Study
- As a: manufacturing engineer
- I want: a pre-registered scenario matrix executed with common random numbers
- So that: differences between scenarios are attributable to the change, not to noise
- Description: Scenario matrix and execution pipeline.
- Acceptance criteria:
  - [ ] Matrix written before runs
  - [ ] Same seeds across scenarios
- Dependencies: none
- Estimate: rollup of child tickets (computed by tools/build_index.py)
- Priority: inherits highest child priority
- Deliverable/artifact: all child deliverables

_Story rollup: 2.5 h_

**[T5.1.1] Pre-registered scenario matrix**
- Type: Task
- Sub-epic: SE5 - Scenario & Bottleneck Study
- Story: S5.1
- Description: Write the scenario matrix before running it: each scenario as a YAML override of baseline v1.0, with the primary and secondary metrics fixed in advance. Suggested levels: inspection station +1; batch size x0.5, x1, x2; staffing +/-1 per role; changeover -25% and -50% (cite SMED literature, flag as judgment); one combination.
- Acceptance criteria:
  - [ ] At least 5 scenarios plus the combination, each a diff against baseline v1.0
  - [ ] Level choices justified; changeover reduction labeled assumption, not a measured SMED result
  - [ ] Primary and secondary metrics listed before any scenario run (git history proves order)
  - [ ] Run budget: scenarios x replications x runtime is at most 1 hour (target)
- Dependencies: T1.1.3, T4.2.1
- Estimate: 1 h (S)
- Priority: P0
- Deliverable/artifact: docs/scenario_matrix.md, configs/scenarios/*.yaml

**[T5.1.2] Run scenarios with common random numbers**
- Type: Task
- Sub-epic: SE5 - Scenario & Bottleneck Study
- Story: S5.1
- Description: Load, validate and run every scenario with the same replication seeds as baseline.
- Acceptance criteria:
  - [ ] Every scenario YAML validates
  - [ ] Unchanged stations use identical random streams to baseline (test)
  - [ ] Parquet results per scenario with config hash
  - [ ] make scenarios runs everything and writes a run log
- Dependencies: T5.1.1, T3.2.3, T3.2.4
- Estimate: 1.5 h (S)
- Priority: P0
- Deliverable/artifact: src/ffdt/experiments/scenarios.py, results/<scenario>/, Makefile target scenarios

---

**[S5.2] Analyze results and name the bottleneck**
- Type: Story
- Sub-epic: SE5 - Scenario & Bottleneck Study
- As a: plant manager
- I want: ranked, statistically supported recommendations and a clear constraint
- So that: I know which investment moves the line and by how much, with uncertainty
- Description: Paired statistics, sensitivity, bottleneck methods, economics, findings memo.
- Acceptance criteria:
  - [ ] Every recommendation carries a CI
  - [ ] Conclusions tested for robustness
- Dependencies: none
- Estimate: rollup of child tickets (computed by tools/build_index.py)
- Priority: inherits highest child priority
- Deliverable/artifact: all child deliverables

_Story rollup: 8 h_

**[T5.2.1] Paired statistical comparison**
- Type: Task
- Sub-epic: SE5 - Scenario & Bottleneck Study
- Story: S5.2
- Description: Per-replication paired differences (scenario minus baseline), t-based 95% CI, bootstrap cross-check, Holm adjustment across scenarios, and a practical-significance threshold labeled as a target (suggested: 2 OEE points).
- Acceptance criteria:
  - [ ] Table: scenario, metric, mean difference, 95% CI, Holm-adjusted p, practical-significance flag
  - [ ] Paired vs unpaired CI width shown to demonstrate CRN benefit
  - [ ] Bootstrap CI agrees with t-CI within a stated tolerance
  - [ ] Unit test: synthetic data with a known difference is recovered
  - [ ] Which comparisons were pre-registered is stated
- Dependencies: T5.1.2
- Estimate: 2 h (M)
- Priority: P0
- Deliverable/artifact: src/ffdt/experiments/stats.py, notebooks/06_scenarios.ipynb, tests/unit/test_stats.py

**[T5.2.2] Sensitivity analysis**
- Type: Task
- Sub-epic: SE5 - Scenario & Bottleneck Study
- Story: S5.2
- Description: One-at-a-time +/-20% perturbation of every Sens=Y assumption in docs/assumptions.md (12 parameters: sub-lot N, minor-stop frequency, buffer capacity, filler rate, AVI rate, MTBF, MTTR, changeover duration, batch size, false-reject rate, defect incidence, QA review) on line OEE and good vials/hour; flag any parameter that flips the bottleneck or reorders scenarios.
- Acceptance criteria:
  - [ ] Tornado chart for OEE and for throughput
  - [ ] Sub-lot size N included to expose discretization error
  - [ ] Written statement of which conclusions survive and which do not
  - [ ] Parameters that flip the bottleneck are listed
- Dependencies: T4.2.1, T3.2.6
- Estimate: 2 h (M)
- Priority: P1
- Deliverable/artifact: src/ffdt/experiments/sensitivity.py, reports/sensitivity.md, figure tornado.png

**[T5.2.3] Bottleneck identification**
- Type: Task
- Sub-epic: SE5 - Scenario & Bottleneck Study
- Story: S5.2
- Description: Apply at least three methods: utilization, active-period method (Roser et al.), and blocking/starvation signature, with queue build-up as a fourth corroboration. Report whether the constraint shifts under each scenario.
- Acceptance criteria:
  - [ ] Method x station table for baseline
  - [ ] Disagreement between methods is explained, not hidden
  - [ ] Per scenario: does the bottleneck shift (yes/no, to where)
  - [ ] Test on a synthetic 3-machine line with a known bottleneck
  - [ ] Caveat stated: with random failures the constraint is dynamic
- Dependencies: T4.2.3, T5.1.2
- Estimate: 1.5 h (S)
- Priority: P0
- Deliverable/artifact: src/ffdt/experiments/bottleneck.py, tests/unit/test_bottleneck.py

**[T5.2.4] Illustrative economics**
- Type: Task
- Sub-epic: SE5 - Scenario & Bottleneck Study
- Story: S5.2
- Description: Translate output gains into value per year using clearly labeled placeholder prices and costs. Not a business case.
- Acceptance criteria:
  - [ ] Value per good vial and capital costs labeled as assumptions with ranges
  - [ ] Simple payback shown with a price sensitivity
  - [ ] States plainly it is illustrative
- Dependencies: T5.2.1
- Estimate: 1 h (S)
- Priority: P2
- Deliverable/artifact: docs/economics.md

**[T5.2.5] Findings memo**
- Type: Task
- Sub-epic: SE5 - Scenario & Bottleneck Study
- Story: S5.2
- Description: Two-page memo for a plant manager: the constraint, ranked scenarios with CIs, what to do first, limitations. results_final.json becomes the only source of resume and README numbers.
- Acceptance criteria:
  - [ ] At most 2 pages
  - [ ] Recommendations ranked by effect size with CIs
  - [ ] Limitations section present
  - [ ] Every number links to a results file
  - [ ] results_final.json frozen
- Dependencies: T5.2.1, T5.2.3
- Estimate: 1.5 h (S)
- Priority: P0
- Deliverable/artifact: reports/scenario_findings.md, reports/results_final.json

---

## SE6 - Interface: Streamlit What-If App

**[S6.1] Run the simulation from a browser**
- Type: Story
- Sub-epic: SE6 - Interface: Streamlit What-If App
- As a: non-technical reviewer
- I want: to set line parameters in a sidebar and see KPIs
- So that: I can explore the line without touching code
- Description: App skeleton and results dashboard.
- Acceptance criteria:
  - [ ] Baseline runs in quick mode in under 30 s (target)
  - [ ] KPIs show plain-language definitions
- Dependencies: none
- Estimate: rollup of child tickets (computed by tools/build_index.py)
- Priority: inherits highest child priority
- Deliverable/artifact: all child deliverables

_Story rollup: 5 h_

**[T6.1.1] Streamlit app skeleton**
- Type: Task
- Sub-epic: SE6 - Interface: Streamlit What-If App
- Story: S6.1
- Description: Sidebar controls bound to the config schema (batch size, staffing per role, changeover scale, inspection stations, MTBF/MTTR scale), validation messages, a Run button and cached results keyed by config hash. The app calls ffdt.api and contains no simulation logic.
- Acceptance criteria:
  - [x] streamlit run app/streamlit_app.py starts the app
  - [x] Invalid inputs blocked with a readable message
  - [x] Baseline run completes in under 30 s in quick mode (target)
  - [x] Second identical run returns in under 1 s from cache
  - [x] No simulation logic in app/
- Dependencies: T2.1.4, T3.2.6
- Estimate: 2 h (M)
- Priority: P0
- Deliverable/artifact: app/streamlit_app.py, src/ffdt/api.py

**[T6.1.2] Results dashboard**
- Type: Task
- Sub-epic: SE6 - Interface: Streamlit What-If App
- Story: S6.1
- Description: KPI tiles (good vials/hour, OEE with A/P/Q, bottleneck utilization, mean batch lead time), loss Pareto, station state timeline for one sample shift, queue times per buffer. Load the dataviz skill before building charts.
- Acceptance criteria:
  - [x] KPI tiles show a plain-language tooltip from the glossary
  - [x] Loss Pareto, state timeline and queue chart render for baseline and any custom run
  - [x] Every view labeled simulated
  - [x] Colorblind-safe palette; works at phone width
- Dependencies: T6.1.1
- Estimate: 3 h (M)
- Priority: P0
- Deliverable/artifact: app/pages or sections in streamlit_app.py

---

**[S6.2] Compare scenarios and share the app**
- Type: Story
- Sub-epic: SE6 - Interface: Streamlit What-If App
- As a: hiring manager
- I want: to compare a scenario to the baseline and open the app from a link
- So that: I can judge the work in under five minutes
- Description: Comparison view, usability polish, deployment, export.
- Acceptance criteria:
  - [ ] Public link works
  - [ ] Two non-technical reviewers finish the task unaided (target)
- Dependencies: none
- Estimate: rollup of child tickets (computed by tools/build_index.py)
- Priority: inherits highest child priority
- Deliverable/artifact: all child deliverables

_Story rollup: 6 h_

**[T6.2.1] Scenario comparison view**
- Type: Task
- Sub-epic: SE6 - Interface: Streamlit What-If App
- Story: S6.2
- Description: Pick baseline versus preset scenarios or a custom run; delta table with CIs; bottleneck highlight and shift.
- Acceptance criteria:
  - [ ] Precomputed preset results load in under 2 s (target)
  - [ ] Custom run uses common random numbers against baseline
  - [ ] Warns when the CI includes zero (no detectable difference)
  - [ ] Bottleneck station highlighted and any shift shown
- Dependencies: T6.1.2, T5.1.2
- Estimate: 2 h (M)
- Priority: P0
- Deliverable/artifact: app section Compare

**[T6.2.2] Non-technical usability polish**
- Type: Task
- Sub-epic: SE6 - Interface: Streamlit What-If App
- Story: S6.2
- Description: Preset buttons for the four required scenarios, glossary expander, how-to-read panel, runaway-run guardrail.
- Acceptance criteria:
  - [ ] Four preset scenario buttons
  - [ ] Glossary expander with the glossary definitions
  - [ ] How to read this panel present
  - [ ] Maximum replications guardrail with explanation
- Dependencies: T6.2.1
- Estimate: 1 h (S)
- Priority: P1
- Deliverable/artifact: app UI text, help panel

**[T6.2.3] Deploy and usability test**
- Type: Task
- Sub-epic: SE6 - Interface: Streamlit What-If App
- Story: S6.2
- Description: Deploy to Streamlit Community Cloud (free; requires a public GitHub repo, so check the repo is safe to publish first). Run a 5-minute task test with 2-3 non-technical reviewers: reduce changeover time by 50% and report the effect.
- Acceptance criteria:
  - [ ] Public URL opens on phone and laptop
  - [ ] At least 2 reviewers complete the task in 5 minutes or less without help (target)
  - [ ] Issues logged; top 2 fixed
  - [ ] No secrets or private data in the repo; cold-start time noted
- Dependencies: T6.2.2
- Estimate: 2 h (M)
- Priority: P1
- Deliverable/artifact: docs/usability_test.md, README link

**[T6.2.4] Export KPI table and charts**
- Type: Task
- Sub-epic: SE6 - Interface: Streamlit What-If App
- Story: S6.2
- Description: CSV download of KPI table and PNG of main charts.
- Acceptance criteria:
  - [x] CSV opens in Excel with units in headers
  - [x] PNG export works for 2 charts
- Dependencies: T6.1.2
- Estimate: 1 h (S)
- Priority: P2
- Deliverable/artifact: app download buttons

---

## SE7 - Documentation & Portfolio Packaging

**[S7.1] Repository documentation and release**
- Type: Story
- Sub-epic: SE7 - Documentation & Portfolio Packaging
- As a: engineer cloning the repo
- I want: a README, model documentation and a reproducible release
- So that: I can rerun the results and understand the limits
- Description: README, model card, release and reproducibility check.
- Acceptance criteria:
  - [ ] Clean-clone reproduction succeeds
  - [ ] README numbers come from results file
- Dependencies: none
- Estimate: rollup of child tickets (computed by tools/build_index.py)
- Priority: inherits highest child priority
- Deliverable/artifact: all child deliverables

_Story rollup: 4 h_

**[T7.1.1] README**
- Type: Task
- Sub-epic: SE7 - Documentation & Portfolio Packaging
- Story: S7.1
- Description: Write the README per planning/05_repo_structure.md outline. All numbers are read from results_final.json by a script, not typed by hand.
- Acceptance criteria:
  - [ ] Sections: summary, problem, method, results, how to run, assumptions, limitations
  - [ ] Three-sentence plain-language summary at the top
  - [ ] Every number marked simulated / benchmark-parameterized
  - [ ] How-to-run verified in a clean clone
  - [ ] Hero figure plus app link or screenshot
- Dependencies: T5.2.5, T6.1.2
- Estimate: 2 h (M)
- Priority: P0
- Deliverable/artifact: README.md

**[T7.1.2] Model card and ODD-style documentation**
- Type: Task
- Sub-epic: SE7 - Documentation & Portfolio Packaging
- Story: S7.1
- Description: Purpose, intended and non-intended use, structure, V&V summary, limitations, version.
- Acceptance criteria:
  - [ ] States intended use as decision-support exploration, not plant release or GxP use
  - [ ] Links to assumptions, verification and baseline definition
  - [ ] Limitations section lists at least 5 items
- Dependencies: T4.2.3
- Estimate: 1 h (S)
- Priority: P1
- Deliverable/artifact: docs/model_card.md

**[T7.1.3] Release and reproducibility check**
- Type: Task
- Sub-epic: SE7 - Documentation & Portfolio Packaging
- Story: S7.1
- Description: Fresh clone, fresh venv, make all reproduces results_final.json. Close out the backlog.
- Acceptance criteria:
  - [ ] make all reproduces results_final.json exactly with the fixed seeds
  - [ ] Tag v1.0.0 created; LICENSE present; repo description and topics set
  - [ ] All ticket statuses updated and tools/build_index.py --check passes
- Dependencies: T7.1.1, T7.2.2
- Estimate: 1 h (S)
- Priority: P0
- Deliverable/artifact: git tag v1.0.0, Makefile target all

---

**[S7.2] Portfolio assets for operations hiring managers**
- Type: Story
- Sub-epic: SE7 - Documentation & Portfolio Packaging
- As a: hiring manager in NJ pharma or food operations
- I want: resume bullets, a pitch and a short deck in operations language
- So that: I can see the candidate's process-improvement judgment quickly
- Description: Figures, 5-slide summary, resume bullets, pitch, Q&A.
- Acceptance criteria:
  - [ ] Every resume number traceable to results_final.json
  - [ ] Simulated nature disclosed
- Dependencies: none
- Estimate: rollup of child tickets (computed by tools/build_index.py)
- Priority: inherits highest child priority
- Deliverable/artifact: all child deliverables

_Story rollup: 3.5 h_

**[T7.2.1] Figures and 5-slide summary**
- Type: Task
- Sub-epic: SE7 - Documentation & Portfolio Packaging
- Story: S7.2
- Description: Five slides per planning/07_portfolio_packaging.md: context, line and model, validation, scenario results and bottleneck, recommendations and limits.
- Acceptance criteria:
  - [ ] Five slides, one message title each
  - [ ] Figures regenerated from results files
  - [ ] PDF exported to docs/portfolio/
  - [ ] Deliverable in 2 minutes spoken
- Dependencies: T5.2.5, T6.2.1
- Estimate: 2 h (M)
- Priority: P1
- Deliverable/artifact: docs/portfolio/slides.pdf (+ source)

**[T7.2.2] Resume bullets, pitch and interview Q&A**
- Type: Task
- Sub-epic: SE7 - Documentation & Portfolio Packaging
- Story: S7.2
- Description: Finalize the three bullets using only numbers from results_final.json, the 60-second pitch, and operations-style interview Q&A.
- Acceptance criteria:
  - [ ] Three bullets in Action + method + quantified result form with real numbers
  - [ ] Each bullet discloses simulated / benchmark-parameterized
  - [ ] 60-second pitch timed at 75 seconds or less
  - [ ] At least 8 Q&A pairs with talking points
  - [ ] Each number traceable to results_final.json
- Dependencies: T5.2.5, T5.2.1
- Estimate: 1.5 h (S)
- Priority: P0
- Deliverable/artifact: docs/portfolio/resume_bullets.md

---

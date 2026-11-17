# Repository and documentation structure

The project folder is itself the repo root (`git init` here when T3.1.1 runs). `planning/` ships in the repo so reviewers can see the process.

```
01_pharma_fill_finish_digital_twin/
├── CLAUDE.md                     # agent operating rules (read first)
├── README.md                     # public face (T7.1.1)
├── Makefile                      # test, lint, scenarios, app, all
├── pyproject.toml
├── requirements.txt              # runtime, exact pins
├── requirements-dev.txt          # -r requirements.txt + dev tools
├── LICENSE                       # MIT (default assumption)
├── .claude/commands/             # next-ticket, close-ticket
├── .github/workflows/ci.yml
├── planning/                     # backlog (exists now)
│   ├── 00_charter.md ... 08_risks_and_open_questions.md
│   ├── 02_stories_and_tickets.md # generated
│   ├── BOARD.md  backlog.csv  backlog.json   # generated
│   └── tickets/se1_.../T1.1.1_*.md           # source of truth, one file per ticket
├── tools/                        # build_index.py, gh_issues.py, check_param_ids.py
├── configs/
│   ├── baseline_line.yaml
│   ├── experiment.yaml           # n replications, seeds
│   └── scenarios/sc_01_add_avi.yaml ...
├── data/
│   ├── raw/benchmark_sources.csv # committed, hand-curated
│   └── processed/                # gitignored
├── src/ffdt/                     # package
│   ├── config.py  params.py  api.py
│   ├── sim/        machine.py failures.py line.py batches.py quality.py staffing.py qa_release.py
│   ├── metrics/    ledger.py oee.py
│   └── experiments/ runner.py scenarios.py stats.py sensitivity.py bottleneck.py
├── app/streamlit_app.py
├── tests/
│   ├── unit/
│   └── verification/             # invariants and analytic checks
├── notebooks/                    # 01_smoke_run, 04_warmup_reps, 05_baseline_report, 06_scenarios
├── results/                      # gitignored raw runs; frozen summaries live in reports/
├── reports/                      # baseline.md, scenario_findings.md, sensitivity.md, results_*.json, figures/
└── docs/
    ├── domain/    process_map.md glossary.md scenario_hypotheses.md sources.md
    ├── adr/       adr_001_entity_granularity.md
    ├── validation/ face_validation_log.md
    ├── assumptions.md  baseline_definition.md  verification.md  metrics_schema.md
    ├── model_card.md  economics.md  usability_test.md
    └── portfolio/ resume_bullets.md slides.pdf
```

## README outline (T7.1.1)
1. Three-sentence plain-language summary + hero figure + app link
2. Problem and business context
3. Method (process modeled, entity design, failures, changeovers, staffing, QA, metrics) with one architecture diagram
4. Results (baseline, bottleneck, scenario table with CIs; numbers from `results_final.json`, all marked simulated)
5. Verification and validation summary and its limits
6. How to run (clean clone: venv, install, `make test`, `make scenarios`, `make app`)
7. Assumptions (top 8, link to register)
8. Limitations and what real plant data would add
9. Repository map, license, citation

## Naming conventions
- Python: `snake_case` modules and functions, `PascalCase` classes; config fields carry unit suffixes (`_min`, `_vpm`, `_vials`, `_pct` as fraction 0-1 named `_frac`).
- Scenario files: `sc_<nn>_<slug>.yaml`. Result folders: `results/<scenario>/<config_hash8>/`.
- Branches: `T3.1.3-machine-process`. Commits: `T3.1.3: add Machine state log`. Tags: `baseline-v1.0`, `v1.0.0`.
- ADRs: `adr_NNN_slug.md`. Assumption IDs `A-001`. Benchmark IDs `B-001` (the `param_id`).
- Every figure title ends with "(simulated, benchmark-parameterized)".

## Requirements file plan
- **Runtime:** simpy, numpy, pandas, scipy, pydantic, pyyaml, joblib, pyarrow, plotly, streamlit.
- **Dev:** pytest, pytest-cov, ruff, jupyter, nbstripout, hypothesis (optional, for property tests).
- Pin exact versions at T3.1.1 by running `pip freeze` after a fresh install on Python 3.12; commit the pins. Re-pin only in a dedicated commit. Do not hand-write version numbers from memory.
- Streamlit Community Cloud reads `requirements.txt`; keep it runtime-only.

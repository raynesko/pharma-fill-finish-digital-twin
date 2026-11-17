# CLAUDE.md: Pharma Fill-Finish Digital Twin

Discrete-event simulation (Python/SimPy) of a sterile vial fill-finish line, with a pre-registered scenario study and a Streamlit what-if app. It is a **resume portfolio project** for NJ operations, process-improvement and quality-analyst roles in pharma/food. The audience is operations hiring managers, not software engineers. Domain correctness and honest quantification matter more than code cleverness.

## Read first
1. `planning/00_charter.md` (scope, non-goals, targets)
2. `planning/BOARD.md` (what is ready now)
3. The ticket file you are working on in `planning/tickets/<sub-epic>/T*.md`
4. `docs/domain/glossary.md` once it exists (metric definitions are binding)

## Working a ticket
1. Pick a ticket: run `python tools/build_index.py`, then take the top item under "Ready now" in `planning/BOARD.md`, or the one the user names. Never start a ticket whose dependencies are not `done`.
2. Set its frontmatter `status: in_progress`.
3. Do the work. Stay inside the ticket's Description and Deliverable. If you find extra work, create a note in the ticket, not new scope.
4. Tick each acceptance-criteria box (`- [x]`) only when it is true and tested. Do not reword criteria to match what you built; if a criterion is wrong, say so to the user.
5. Set `status: done`, run `python tools/build_index.py --check`, then `python tools/build_index.py`.
6. Commit only when the user asks. Message format: `T3.1.3: short summary`.

Slash commands: `/next-ticket`, `/close-ticket <ID>`.

## Hard rules (project integrity)
- **No invented data.** Every model parameter traces to a row in `data/raw/benchmark_sources.csv` (`param_id`) or is tagged `engineering_judgment` with a reason. Placeholder values in the charter are not citable.
- **Label every number**: TARGET (plan), PLACEHOLDER, ASSUMPTION, or RESULT (with a link to a results file). Never present a target as achieved.
- **Do not guess domain facts.** If unsure about GMP, equipment speeds, regulatory clause numbers or benchmarks, write "VERIFY" and add it to the SME list in T1.1.1 or `planning/08_risks_and_open_questions.md`. Do not cite a regulation section you have not read.
- **Pre-registration:** `docs/domain/scenario_hypotheses.md` and `docs/scenario_matrix.md` must be committed before scenario runs. Do not edit them afterward except to add dated amendments.
- **One source for public numbers:** README, slides and resume bullets read from `reports/results_final.json` only.
- **Everything is simulated.** Figures and text say "simulated, benchmark-parameterized". Never imply plant data.
- Baseline is frozen at tag `baseline-v1.0`. Changing baseline parameters requires a v1.1 and a changelog.
- Out of scope (do not add): lyophilization, formulation, media-fill modeling, deviations/CAPA workflows, real plant data, GxP validation claims.

## Technical conventions
- Python 3.12, package `ffdt` under `src/`, tests in `tests/unit` and `tests/verification`.
- Time unit **minutes**; rates **vials/min**; field names carry unit suffixes (`_min`, `_vpm`, `_vials`, `_frac`).
- Entities are sub-lots (default 100 vials) per ADR-001 (once written, that ADR governs).
- All randomness through `numpy.random.Generator` from `SeedSequence.spawn` (per station, per replication). No global RNG. This is what enables common random numbers.
- Metrics are computed only from the state ledger (`ffdt.metrics` must not import `ffdt.sim`).
- The Streamlit app calls `ffdt.api` and contains no simulation logic.
- Charts: load the `dataviz` skill first; colorblind-safe palettes.
- Do not guess dependency versions; pin from `pip freeze` at T3.1.1.

## Commands (T3.1.1 done)
Windows has no `make`; use the task runner (the Makefile just wraps it):
`.venv\Scripts\python tasks.py test|lint|fix|scenarios|app|all` (or `make test` where make exists).
Env: `.venv/` is local and gitignored; recreate with `python -m venv .venv && .venv\Scripts\pip install -r requirements-dev.txt && .venv\Scripts\pip install -e .`
`python tools/build_index.py [--check]` is stdlib only and works with any Python.

## Layout
`planning/` backlog and plan (tickets are the source of truth; `BOARD.md`, `backlog.csv`, `backlog.json`, `02_stories_and_tickets.md` are generated; never hand-edit generated files). Full tree in `planning/05_repo_structure.md`.

## Domain cheat sheet
OEE = Availability x Performance x Quality. Changeover is an availability loss here; QA hold time is **not** an equipment loss and is reported as batch lead time. Starvation (no input) and blocking (output full) are separate from breakdowns. Line clearance is a GMP step; 21 CFR 211.130(e) covers packaging/labeling only, fill-area citation is VERIFY (see docs/domain/process_map.md). Bottleneck is an output of the model, never an input.

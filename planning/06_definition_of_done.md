# Definition of Done

## Ticket
- [ ] Every acceptance-criteria box in the ticket file is ticked (not reworded to fit what was built)
- [ ] The named deliverable exists at the stated path
- [ ] Tests for new code pass locally (`make test`) and `make lint` is clean
- [ ] Any new parameter has a `param_id` in `benchmark_sources.csv` or a judgment tag, and an entry in `docs/assumptions.md`
- [ ] Any number stated in a doc is labeled TARGET, PLACEHOLDER, ASSUMPTION or RESULT with a file link
- [ ] Ticket frontmatter `status: done`; `python tools/build_index.py --check` passes
- [ ] Commit message starts with the ticket ID

## Sub-epic
- [ ] All P0 tickets done; P1/P2 either done or `status: cut` with a one-line reason in the ticket
- [ ] Exit criteria in `01_epic_breakdown.md` met
- [ ] Docs touched by the sub-epic are consistent with each other (glossary vs code, assumptions vs YAML)
- [ ] `BOARD.md` regenerated and committed

## Project (v1.0.0)
- [ ] Verification suite green in CI; analytical errors within targets or the miss is documented
- [ ] Baseline tag `baseline-v1.0` unmodified; scenario matrix committed before scenario runs
- [ ] `reports/results_final.json` frozen; README and resume numbers come only from it
- [ ] Every claim is labeled simulated; limitations section lists at least 5 items
- [ ] `make all` in a fresh clone reproduces results
- [ ] Non-technical usability test run, or ticket explicitly cut
- [ ] Resume bullets, 60-second pitch and Q&A done (T7.2.2)
- [ ] No secrets, personal data or confidential plant information in the repo

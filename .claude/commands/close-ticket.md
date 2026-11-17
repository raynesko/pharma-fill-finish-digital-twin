---
description: Verify acceptance criteria and mark a ticket done
argument-hint: <ticket ID, e.g. T3.1.3>
---
1. Open the ticket file for `$ARGUMENTS` in `planning/tickets/`.
2. For each acceptance criterion, verify it is actually true (run the test, open the artifact). Do not tick from memory.
3. Tick verified boxes `- [x]`. If any box cannot be ticked, leave the ticket `in_progress` and report which criterion fails and why.
4. If all are ticked: set `status: done`, run `python tools/build_index.py --check`, then `python tools/build_index.py`.
5. Report the deliverable path and the next ready ticket. Do not commit unless asked.

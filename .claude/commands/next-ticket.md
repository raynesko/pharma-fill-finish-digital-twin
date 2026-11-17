---
description: Pick the next ready ticket and start it
---
1. Run `python tools/build_index.py` and read `planning/BOARD.md`.
2. Choose the first item under "Ready now" (or `$ARGUMENTS` if a ticket ID was given). Confirm every dependency is `done` or `cut`.
3. Read the ticket file in `planning/tickets/` and `CLAUDE.md` hard rules.
4. Set its frontmatter `status: in_progress`.
5. Summarize in 5 lines: goal, deliverable path, acceptance criteria, risks. Then begin the work.

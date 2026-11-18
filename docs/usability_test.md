# Usability test protocol (T6.2.3)

Status: **protocol ready, not yet run.** Results below are empty until real sessions happen; nothing here may be filled in without a real reviewer.

## Goal
Check that a non-technical person can use the what-if app to answer a plant question without help. TARGET (charter): at least 2 of 2-3 reviewers finish the task in 5 minutes or less with no help.

## Reviewers
2-3 people who have not seen the app and do not write code (for example an operations or quality classmate, a family member in any industry). Record only a role, never a name.

## Setup
- The deployed app URL, opened fresh on the reviewer's own phone or laptop (note which).
- Note the **cold-start time**: seconds from opening the URL to the page being usable (Streamlit Community Cloud apps sleep when idle).
- Moderator reads the script and stays silent afterwards; answer no questions until the task ends or 5 minutes pass.

## Script (read aloud)
> "This is a simulated filling line for medicine vials; the numbers are not from a real plant. A plant manager asks: if we cut every changeover time in half, how many more good vials per hour would we make, and is that difference real or could it be noise? Please find the answer using this page, and think aloud while you do. I can't help during the task."

## Success criteria
Reviewer states **all three**:
1. the change in good vials per scheduled hour (about +25%, or the vials/h number);
2. that the difference is real (the confidence range does not include zero / "detectable: yes");
3. which station is the bottleneck (filler).

Either path counts: the "Changeovers 50% shorter" button, or the sidebar slider at 0.5 + Run in the Compare view.

## Log
| # | Reviewer role | Device | Cold start (s) | Time to answer (min:s) | Success (1/2/3) | Needed help? | Where they hesitated |
|---|---|---|---|---|---|---|---|
| 1 | | | | | | | |
| 2 | | | | | | | |
| 3 | | | | | | | |

## Issues found
| Issue | Seen by (#) | Severity | Fix | Fixed? |
|---|---|---|---|---|
| | | | | |

The top 2 issues by severity are fixed before closing T6.2.3.

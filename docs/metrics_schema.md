# Metrics output schema

Ticket T3.2.5. Definitions are binding from `docs/domain/glossary.md`. Time is in minutes unless a column says `_h`. `ffdt.metrics` reads only the plain dict below and imports nothing from `ffdt.sim`.

## 1. Run export: `Line.export()` → dict
| Key | Type | Meaning |
|---|---|---|
| `config_name`, `config_hash` | str | Config identity (`LineConfig.hash()`, 12 hex chars) |
| `root_seed`, `replication` | int | Random-stream identity (common random numbers) |
| `completed` | bool | All batches packed before `max_min` |
| `horizon_min` | float | Campaign end: last vial packed (or `max_min` if not completed). Equipment metrics stop here. QA continues after it |
| `off_shift` | list[(start, end)] | Off-shift intervals inside [0, horizon] |
| `stations` | list[{station, rate_vpm, units, offline?}] | Config order. `manual_inspection` is appended with `offline: true` |
| `states` | list[(station, unit, state, start, end)] | Raw state log (before the calendar overlay) |
| `outputs` | list[(station, unit, time, batch_id, vials_in, vials_out)] | One row per sub-lot processed. `vials_in - vials_out` = rejected at that station |
| `events` | list[(time, kind, station, detail)] | `breakdown`, `minor_stop`, `changeover` (detail = unit, type, to_batch, minutes), `batch_complete` |
| `queues` | list[(buffer, time, delta, uid, vials)] | Entry (+1) and exit (-1) of every buffer, named `in:<station>` |
| `flow` | list[(time, kind, batch_id, vials)] | `started` / `packed` / `scrapped` |
| `batches` | list[dict] | batch_id, product, format, size, start_min, end_min, packed, scrapped, qa_queue_min, review_min, release_min |
| `started`, `packed`, `scrapped` | int | Vial ledger. `started = packed + scrapped` for a completed run |
| `scrap_by_cause` | {cause: vials} | `fill_weight`, `avi_confirmed` |
| `escapes` | int | True defects packed (quality-risk metric, not a yield loss) |

## 2. Derived tables (`ffdt.metrics`)
| Function | Output | Columns |
|---|---|---|
| `ledger.states_df` | DataFrame | station, unit, state, start, end, minutes |
| `ledger.calendar_overlay` | DataFrame | Same columns. Any off-shift part of a non-planned interval becomes `PLANNED_STOP`, so every unit's PLANNED_STOP equals the off-shift minutes |
| `ledger.state_minutes` | DataFrame (station × 8 states) | Minutes summed over units |
| `ledger.batches_df` | DataFrame | batch columns + `cycle_time_min` (start → last packed), `lead_time_min` (start → QA release), `yield` |
| `ledger.queue_stats` | DataFrame per buffer | `mean_sublots`, `mean_vials` (time-weighted L), `max_sublots`, `arrivals`, `lambda_per_min`, `mean_wait_min` (W from matched entry/exit), `littles_ratio` = L / (λW) |
| `ledger.wip_stats` | dict | `wip_mean_vials` (time-weighted), `wip_max_vials` |
| `oee.station_table` | DataFrame per station | `ppt_min`, `operating_min`, `A`, `P`, `Q`, `OEE`, `utilization`, `processed`, `good`, `good_per_ppt_hour`, `<STATE>_min` × 8 |
| `oee.line_oee` | dict | `reference_station`, `definition`, `A`, `P`, `Q`, `OEE`, `ppt_min` (D4) |
| `oee.loss_pareto` | DataFrame | `category`, `share_of_ppt`, `six_big_loss`, `factor`. Shares sum to 1 − line OEE |
| `oee.summarize` | dict (one row per replication) | see section 3 |

### Notes
- For a station with several units (SC-01's second AVI), PPT and state minutes are summed over units and the rate is per unit, so OEE = good / (PPT_sum × rate).
- For `manual_inspection`, "good" means vials returned to the flow. Its OEE is shown only for completeness. Read its `utilization` as inspector utilization.
- The loss Pareto is taken at the reference station (filler). Its `STARVED`/`BLOCKED` shares are flow losses caused by other stations (D3). `other` is the residual and is ~0 for a completed run.

## 3. Replication summary (`oee.summarize`), the scenario metrics
| Column | Primary? | Definition |
|---|---|---|
| `good_per_ppt_hour` | **Primary** | Good vials packed / reference-station PPT hours. Not affected by weekend spill (see planning/08). Fixed by amendment A1 in `scenario_hypotheses.md` |
| `line_oee`, `line_A`, `line_P`, `line_Q` | Primary | D4 |
| `good_per_calendar_hour` | Secondary | Good vials / makespan hours (includes nights and weekends) |
| `makespan_h` | Secondary | Campaign start → last vial packed |
| `good_vials`, `yield`, `escapes` | Secondary | Vial ledger |
| `mean_cycle_time_h`, `mean_lead_time_h`, `mean_qa_queue_h` | Secondary | Per-batch means (D5: lead time includes QA) |
| `wip_mean_vials`, `wip_max_vials` | Secondary | Time-weighted WIP |
| `config_hash`, `root_seed`, `replication`, `completed` | Keys | |

Primary metric fixed by amendment A1 (2026-11-17). See the weekend-spill finding in `planning/08_risks_and_open_questions.md`.

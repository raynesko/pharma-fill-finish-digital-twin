# ADR-001: Entity granularity and time unit

Status: accepted · Ticket T3.1.2 · Date: 2026-11-15

## Context
The line processes on the order of one million vials per week at the PLACEHOLDER filler rate of 240 vpm. A SimPy entity per vial means every vial costs several events at every station. The model needs about 30 replications per scenario, several scenarios and a 30-second interactive "quick mode", so runtime matters. Entities must still allow vial-level quality accounting and realistic blocking/starvation.

Prototype: `tools/adr001_benchmark.py` (one machine, finite buffer of 5,000 vials, one-week campaign of 4,800 min, operation-dependent exponential breakdowns, preemptive-resume). All parameters are placeholders; this measures runtime and discretization only, not line behavior. Machine: the builder's Windows laptop, Python 3.12, SimPy 4.1.2.

## Measurements (one machine, one simulated week)
| Vials per entity | Mean runtime / replication | Vials out, same seeds 0-2 |
|---|---|---|
| 1 (vial-level) | 5.75 s (3 reps) | 1,078,034 / 1,099,749 / 1,064,909 |
| 10 | 0.51 s (10 reps) | 1,078,030 / 1,099,740 / 1,064,900 |
| **100** | **0.049 s (10 reps)** | 1,078,000 / 1,099,700 / 1,064,900 |
| 500 | 0.010 s (10 reps) | 1,078,000 / 1,099,500 / 1,064,500 |

- Runtime scales about linearly with entity count: vial-level is roughly 115x slower than N=100.
- With identical seeds the output differs from vial-level by at most N vials per run (the partial entity at the horizon), under 0.05% at N=500 in these runs.
- Projection (not yet measured): 8 stations at N=100 is about 0.4 s of kernel time per replication; state logging and metrics may add a multiple. The 10 s target for a full baseline replication should hold with margin. **Re-verified in T3.1.5: the full 7-station baseline campaign runs in about 0.5 s per replication** (3 seeds, before quality, changeovers and staffing were wired). Vial-level would be near 45 s per replication for the kernel alone, which fails the target and the app's 30 s quick mode.

## Decision
1. **Entities are sub-lots of N vials, default N = 100**, configurable (`sublot_vials` in the config) and included in the sensitivity analysis (T5.2.2, with N in {10, 100, 500}).
2. **Sub-lot size and buffer capacity** are specified in vials in the config; internal capacity is `max(1, floor(vials / N))` sub-lots.
3. **Batch sizes need not be multiples of N**: the last sub-lot of a batch may be smaller; entities carry their own vial count and processing time = vials / rate.
4. **Quality at vial resolution inside the sub-lot**: an inspection station draws rejects for a sub-lot from a binomial on its vial count and passes the sub-lot on with fewer vials (an entity with 0 vials is dropped). Quality therefore keeps vial-level resolution without vial-level events.
5. **Time unit: minutes** (floats). Rates are vials per minute. Config field names carry unit suffixes.
6. **Operation-dependent failures** use a failure clock that advances only while the station is processing (matches the prototype).

## Consequences
- **Good:** fast replications (supports 30 reps x many scenarios and an interactive app); simple event log.
- **Cost, accuracy:** a sub-lot moves through a station as a unit, so blocking and starvation transitions are quantized to about N / rate minutes (0.4 min at N=100 and 240 vpm); stoppages shorter than that are not resolved well, so **minor stoppages must be modeled as time added to processing or as state intervals independent of entity boundaries, not as entity events**. Small buffers (near N vials) lose fidelity; baseline buffers must stay at least 10 sub-lots (a check in config validation).
- **Untested by this prototype:** effects on multi-station blocking dynamics and on reject accounting. These are tested by the N sensitivity run in T5.2.2; if results at N=10 and N=100 differ by more than the CI half-width, N=100 is rejected for the headline results and the finding is reported.
- **Reversible:** granularity is a config parameter, so revising N does not change code.

## Alternatives rejected
- Vial-level entities: accurate but too slow (above).
- Continuous-flow (fluid) model: very fast but loses discrete batches, changeovers and blocking structure the study is about.

# Bottleneck identification

Ticket T5.2.3. **Simulated, benchmark-parameterized. Not plant data.** Every number is a RESULT from `results/bottleneck_evidence.parquet` and `results/bottleneck_verdicts.csv` (`python -m ffdt.experiments.bottleneck`), 30 replications per configuration, same seeds as the scenario study. Methods and references: docstring of `src/ffdt/experiments/bottleneck.py`.

## Baseline: method x station
Shares are of scheduled production time (PPT), mean over replications. Bold = the station each method picks.

| Station | Utilization | Starved | Blocked | Active-period sole | Active-period shifting | Arrow method pick | Queue in front, sub-lots |
|---|---|---|---|---|---|---|---|
| washer | 39.4% | 1.6% | 48.3% | 1.5% | 3.0% | 0% of reps | n/a (release buffer) |
| tunnel | 39.4% | 3.3% | 48.8% | 0.2% | 0.8% | 0% of reps | 16.8 |
| filler | **57.5%** | 1.8% | 10.0% | **61.9%** | 14.4% | 100% of reps | **18.7** |
| capper | 45.9% | 26.9% | 10.2% | 0.5% | 1.1% | 0% of reps | 2.9 |
| avi | 45.9% | 25.0% | 7.3% | 1.8% | 3.7% | 0% of reps | 4.3 |
| labeler | 45.8% | 25.8% | 5.5% | 3.2% | 2.8% | 0% of reps | 4.0 |
| cartoner | 49.1% | 21.0% | 0.0% | 13.6% | 11.8% | 0% of reps | 4.4 |

**All four methods pick `filler`** (utilization in 100% of replications, active period 100%, arrows 100%, queue 100%).

## Where the methods differ, and why
- **The constraint is not fully utilized.** The filler runs only 57% of scheduled time, yet it is the constraint: it is almost never starved or blocked, and most of its lost time is its own changeovers (see `reports/baseline.md`). Utilization alone would undersell how binding it is; the starved/blocked signature and the active-period method show it.
- **A secondary, shifting bottleneck.** The active-period method finds the cartoner as the second bottleneck in 30 of 30 replications (14% sole and 12% shifting share of PPT). It is the slowest station after the filler, is never blocked (it is last) and loses time waiting for operators. That is consistent with the filler being blocked by downstream stations about 10% of the time. The run-level methods cannot see a secondary bottleneck because they summarize the whole run.
- **Queue method minority picks.** In a few replications of some scenarios the queue method picks the tunnel. When the filler is blocked the blockage propagates upstream, so the buffers in front of both the filler and the tunnel sit near their cap of 20 sub-lots and small differences decide the pick. This is why queue length is used only as corroboration.

## Does the constraint shift under each scenario?
| Scenario | Consensus | Methods agreeing (of 4) | Shift vs baseline | Weakest method agreement |
|---|---|---|---|---|
| baseline | filler | 4 | no | utilization 100% |
| sc01_avi_plus1 | filler | 4 | no | queue 97% |
| sc02_batch_x0p5 | filler | 4 | no | active_period 97% |
| sc02_batch_x2 | filler | 4 | no | queue 93% |
| sc03_inspector_minus1 | filler | 4 | no | utilization 100% |
| sc03_inspector_plus1 | filler | 4 | no | utilization 100% |
| sc03_mechanic_plus1 | filler | 4 | no | utilization 100% |
| sc03_operator_minus1 | filler | 4 | no | utilization 100% |
| sc03_operator_plus1 | filler | 4 | no | utilization 100% |
| sc04_changeover_m25 | filler | 4 | no | queue 90% |
| sc04_changeover_m50 | filler | 4 | no | utilization 100% |
| sc05_combo_co50_avi2 | filler | 4 | no | utilization 100% |

No scenario moves the constraint off the filler at the levels tested. Changeover reduction (SC-04) attacks the filler's largest loss directly, which is consistent with it being the largest effect in the scenario study; adding AVI capacity (SC-01) adds capacity at a non-constraint. Hypothesis verdicts are written in the findings memo (T5.2.5).

## Caveat: the constraint is dynamic
With random breakdowns, minor stops, changeovers and staffing waits, the constraint moves during a run. The active-period method measures this directly: the filler is the sole bottleneck 62% of PPT, not 100%. A station named the constraint here is the one that limits output most of the time, under these benchmark parameters. Different real-line speeds, reliability or staffing could move it, which is why the method is part of the model and not an input.

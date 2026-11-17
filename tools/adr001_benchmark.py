"""ADR-001 prototype: one-machine SimPy line at several entity sizes (vials per entity).

Measures wall-clock runtime and output for a one-week campaign (5 days x 2 shifts x 8 h = 4800 min)
at a PLACEHOLDER filler rate of 240 vpm with operation-dependent breakdowns (PLACEHOLDER MTBF/MTTR).
Not model code: a throwaway benchmark to support docs/adr/adr_001_entity_granularity.md.

    python tools/adr001_benchmark.py
"""

import statistics
import time

import numpy as np
import simpy

HORIZON_MIN = 4800.0
RATE_VPM = 240.0  # PLACEHOLDER
MTBF_MIN = 240.0  # PLACEHOLDER (operating time between failures)
MTTR_MIN = 20.0  # PLACEHOLDER
BUFFER_ENTITIES_VIALS = 5000  # buffer capacity in vials, held constant across entity sizes


def run_once(entity_vials: int, seed: int) -> tuple[float, int, int]:
    rng = np.random.default_rng(seed)
    env = simpy.Environment()
    cap = max(1, BUFFER_ENTITIES_VIALS // entity_vials)
    buf = simpy.Store(env, capacity=cap)
    out = {"vials": 0}
    proc_time = entity_vials / RATE_VPM
    events = {"n": 0}

    def source():
        while True:
            yield buf.put(entity_vials)  # infinite upstream supply, blocked by buffer capacity

    def machine():
        ttf = rng.exponential(MTBF_MIN)
        while True:
            vials = yield buf.get()
            remaining = proc_time
            while remaining > 1e-12:
                step = min(remaining, ttf)
                yield env.timeout(step)
                events["n"] += 1
                remaining -= step
                ttf -= step
                if ttf <= 1e-12:  # breakdown while running; repair, then resume (preemptive-resume)
                    yield env.timeout(rng.exponential(MTTR_MIN))
                    ttf = rng.exponential(MTBF_MIN)
            out["vials"] += vials

    env.process(source())
    env.process(machine())
    t0 = time.perf_counter()
    env.run(until=HORIZON_MIN)
    return time.perf_counter() - t0, out["vials"], events["n"]


def main():
    print("PLACEHOLDER parameters; benchmark of runtime and discretization only")
    print(
        f"{'vials/entity':>12} {'runtime s (mean)':>17} {'vials out (mean)':>17} {'sd':>9} {'timeouts':>9}"
    )
    for n in (1, 10, 100, 500):
        reps = 3 if n == 1 else 10
        res = [run_once(n, seed) for seed in range(reps)]
        rt = statistics.mean(r[0] for r in res)
        vials = [r[1] for r in res]
        print(
            f"{n:>12} {rt:>17.3f} {statistics.mean(vials):>17.0f} "
            f"{statistics.stdev(vials):>9.0f} {int(statistics.mean(r[2] for r in res)):>9}"
        )


if __name__ == "__main__":
    main()

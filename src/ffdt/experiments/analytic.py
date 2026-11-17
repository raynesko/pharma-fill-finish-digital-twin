"""Analytical cross-checks of the simulation primitives (T4.1.2).

The real ``Machine`` and ``MonitoredStore`` classes are configured as textbook queues and
compared with closed forms:

  M/M/1      Poisson arrivals into an unbounded buffer, one Machine. Service time = vials / rate;
             sub-lot sizes are geometric with a large mean, so service is exponential to within
             0.05% in the second moment. Theory uses Pollaczek-Khinchine with the exact moments:
             Wq = lambda E[S^2] / (2 (1 - rho)), which is lambda / (mu (mu - lambda)) for M/M/1.
  M/M/1/K    Same, but arrivals that find K in the system (buffer K-1 + 1 in service) are lost.
             P_block = (1 - rho) rho^K / (1 - rho^(K+1)) (PASTA: fraction of arrivals blocked).
  Availability  A single always-fed Machine with operation-dependent failures:
             A = MTBF / (MTBF + MTTR) (fraction of non-idle time in RUN).

Each function returns one value per replication so callers can build t-based 95% CIs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import simpy
from scipy import stats

from ffdt.config import Failures
from ffdt.rng import stream
from ffdt.sim.core import MonitoredStore, SimLog, SubLot
from ffdt.sim.failures import RunClocks
from ffdt.sim.machine import Machine

RATE = 1000.0  # vials per minute: with mean sub-lot 1000 vials, mean service = 1 min


@dataclass
class Check:
    name: str
    theory: float
    mean: float
    ci_low: float
    ci_high: float
    n_reps: int

    @property
    def rel_error(self) -> float:
        return (self.mean - self.theory) / self.theory

    @property
    def theory_in_ci(self) -> bool:
        return self.ci_low <= self.theory <= self.ci_high


def t_ci(x, level: float = 0.95) -> tuple[float, float, float]:
    x = np.asarray(x, dtype=float)
    m, n = float(x.mean()), len(x)
    h = float(stats.t.ppf((1 + level) / 2, n - 1) * x.std(ddof=1) / math.sqrt(n))
    return m, m - h, m + h


def _geometric_vials(rng, mean_vials: float) -> int:
    return int(rng.geometric(1.0 / mean_vials))


def service_moments(mean_vials: float) -> tuple[float, float]:
    """E[S], E[S^2] for S = V / RATE with V ~ Geometric(p = 1/mean) on {1, 2, ...}."""
    p = 1.0 / mean_vials
    ev, ev2 = 1 / p, (2 - p) / p**2
    return ev / RATE, ev2 / RATE**2


def _mm1_rep(lam, mean_vials, n_customers, seed, rep, capacity_k=None):
    env, log = simpy.Environment(), SimLog()
    cap = math.inf if capacity_k is None else capacity_k - 1
    buf = MonitoredStore(env, "q", log, capacity=cap)
    out = simpy.Store(env)
    m = Machine(env, "server", RATE, buf, out, log)
    arr, size = stream(seed, rep, "mm1.arrivals"), stream(seed, rep, "mm1.sizes")
    counts = {"arrivals": 0, "blocked": 0}

    def source():
        for _ in range(n_customers):
            yield env.timeout(float(arr.exponential(1 / lam)))
            counts["arrivals"] += 1
            in_system = len(buf.items) + (m.holding is not None)
            if capacity_k is not None and in_system >= capacity_k:
                counts["blocked"] += 1
                continue
            buf.put(SubLot(0, "p", "f", _geometric_vials(size, mean_vials)))

    env.process(source())
    env.run()
    q = log.queues
    t_in = {uid: t for _b, t, d, uid, _v in q if d > 0}
    waits = [t - t_in[uid] for _b, t, d, uid, _v in q if d < 0]
    return float(np.mean(waits)), counts["blocked"] / counts["arrivals"]


def mm1_wait(rho=0.5, mean_vials=1000, n_customers=20_000, n_reps=30, seed=1) -> Check:
    es, es2 = service_moments(mean_vials)
    lam = rho / es
    theory = lam * es2 / (2 * (1 - rho))
    x = [_mm1_rep(lam, mean_vials, n_customers, seed, r)[0] for r in range(n_reps)]
    m, lo, hi = t_ci(x)
    return Check(f"M/M/1 mean queue wait Wq (rho={rho}), min", theory, m, lo, hi, n_reps)


def mm1k_block(rho=0.8, k=5, mean_vials=1000, n_customers=20_000, n_reps=30, seed=2) -> Check:
    es, _ = service_moments(mean_vials)
    lam = rho / es
    theory = (1 - rho) * rho**k / (1 - rho ** (k + 1))
    x = [_mm1_rep(lam, mean_vials, n_customers, seed, r, capacity_k=k)[1] for r in range(n_reps)]
    m, lo, hi = t_ci(x)
    return Check(f"M/M/1/K blocking probability (rho={rho}, K={k})", theory, m, lo, hi, n_reps)


def availability(mtbf=240.0, mttr=20.0, cv=0.8, horizon=200_000.0, n_reps=30, seed=3) -> Check:
    f = Failures(mtbf_min=mtbf, mttr_mean_min=mttr, mttr_cv=cv)
    x = []
    for r in range(n_reps):
        env, log = simpy.Environment(), SimLog()
        inbuf, out = simpy.Store(env), simpy.Store(env)
        big = 100_000  # 100 min of work per sub-lot: few events, never starved
        for _ in range(int(horizon * RATE / big) + 10):
            inbuf.items.append(SubLot(0, "p", "f", big))
        clocks = RunClocks(f, None, seed, r, "avail")
        m = Machine(env, "m", RATE, inbuf, out, log, clocks=clocks)
        env.run(until=horizon)
        m.rec.close()
        run = sum(b - a for *_x, s, a, b in log.states if s == "RUN")
        down = sum(b - a for *_x, s, a, b in log.states if s == "DOWN")
        x.append(run / (run + down))
    mean, lo, hi = t_ci(x)
    return Check(
        f"Availability MTBF/(MTBF+MTTR) ({mtbf:g}/{mttr:g})",
        mtbf / (mtbf + mttr),
        mean,
        lo,
        hi,
        n_reps,
    )

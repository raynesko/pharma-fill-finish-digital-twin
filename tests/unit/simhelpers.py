"""Small builders for unit tests of the simulation core."""

import simpy

from ffdt.sim.core import SimLog, SubLot
from ffdt.sim.machine import Machine


def source(env, buf, n_sublots, vials=100, batch_id=0):
    for i in range(n_sublots):
        yield buf.put(SubLot(batch_id, "p", "f", vials, last_in_batch=(i == n_sublots - 1)))


def sink(env, buf, done, n_sublots, out):
    for _ in range(n_sublots):
        item = yield buf.get()
        out.append((env.now, item))
    done.succeed()


def serial_line(rates, n_sublots, buffer_sublots=10, vials=100, **machine_kw):
    """Source -> machines in series -> sink. Returns (env, log, machines, packed, done, bufs)."""
    env, log = simpy.Environment(), SimLog()
    bufs = [simpy.Store(env, capacity=buffer_sublots) for _ in range(len(rates))]
    bufs.append(simpy.Store(env))  # unlimited sink buffer
    machines = [
        Machine(env, f"m{i}", r, bufs[i], bufs[i + 1], log, **machine_kw)
        for i, r in enumerate(rates)
    ]
    packed, done = [], env.event()
    env.process(source(env, bufs[0], n_sublots, vials))
    env.process(sink(env, bufs[-1], done, n_sublots, packed))
    return env, log, machines, packed, done, bufs


def state_minutes(log, station):
    tot = {}
    for st, _u, s, a, b in log.states:
        if st == station:
            tot[s] = tot.get(s, 0.0) + b - a
    return tot

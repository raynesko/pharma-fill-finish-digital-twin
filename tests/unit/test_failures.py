import pytest
import simpy
from simhelpers import serial_line, state_minutes

from ffdt.config import Failures, MinorStops
from ffdt.sim.core import SimLog, SubLot
from ffdt.sim.failures import RunClocks, Stop
from ffdt.sim.machine import Machine


def isolated_machine(failures, minor, seed=7, horizon=300_000, rate=100):
    """Machine with unlimited supply and unlimited output; runs until ``horizon``."""
    env, log = simpy.Environment(), SimLog()
    inbuf, outbuf = simpy.Store(env, capacity=5), simpy.Store(env)

    def supply():
        while True:
            yield inbuf.put(SubLot(0, "p", "f", 100))

    env.process(supply())
    clocks = RunClocks(failures, minor, seed, 0, "m")
    m = Machine(env, "m", rate, inbuf, outbuf, log, clocks=clocks)
    env.run(until=horizon)
    m.rec.close()
    return log, outbuf


def test_long_run_availability_matches_formula():
    f = Failures(mtbf_min=100, mttr_mean_min=10, mttr_cv=0.8)
    log, _ = isolated_machine(f, None)
    st = state_minutes(log, "m")
    a = st["RUN"] / (st["RUN"] + st["DOWN"])
    assert a == pytest.approx(100 / 110, rel=0.02)  # within 2% (target)


def test_preemptive_resume_loses_no_work():
    f = Failures(mtbf_min=0.5, mttr_mean_min=0.2, mttr_cv=0.5)  # many interruptions per item
    env, log, ms, packed, done, _ = serial_line([200], 500, clocks=RunClocks(f, None, 3, 0, "m0"))
    env.run(until=done)
    ms[0].rec.close()
    assert sum(i.vials for _t, i in packed) == 500 * 100  # nothing lost or duplicated
    st = state_minutes(log, "m0")
    assert st["RUN"] == pytest.approx(500 * 100 / 200)  # exactly the work content
    assert sum(1 for e in log.events if e[1] == "breakdown") > 100


def test_breakdowns_and_minor_stops_are_separate_categories():
    f = Failures(mtbf_min=200, mttr_mean_min=20, mttr_cv=0.8)
    mi = MinorStops(mean_between_min=20, mean_duration_min=1)
    log, _ = isolated_machine(f, mi, horizon=50_000)
    st = state_minutes(log, "m")
    n_minor = sum(1 for e in log.events if e[1] == "minor_stop")
    n_down = sum(1 for e in log.events if e[1] == "breakdown")
    assert st["MINOR_STOP"] > 0 and st["DOWN"] > 0
    assert n_minor > 5 * n_down  # minor stops roughly 10x more frequent per run minute
    assert st["MINOR_STOP"] / n_minor == pytest.approx(1, rel=0.15)


def test_same_seed_same_event_log_different_seed_differs():
    f = Failures(mtbf_min=100, mttr_mean_min=10, mttr_cv=0.8)
    mi = MinorStops(mean_between_min=30, mean_duration_min=1)
    a, _ = isolated_machine(f, mi, seed=11, horizon=20_000)
    b, _ = isolated_machine(f, mi, seed=11, horizon=20_000)
    c, _ = isolated_machine(f, mi, seed=12, horizon=20_000)
    assert a.events == b.events and a.states == b.states
    assert a.events != c.events


def test_clock_advance_semantics():
    clocks = RunClocks(Failures(mtbf_min=50, mttr_mean_min=5, mttr_cv=0.5), None, 1, 0, "k")
    ttf = clocks.ttf
    assert clocks.advance(ttf / 2) is None
    assert clocks.advance(ttf / 2) is Stop.BREAKDOWN
    assert clocks.ttf > 0  # redrawn


def test_repair_waits_for_mechanic():
    f = Failures(mtbf_min=10, mttr_mean_min=5, mttr_cv=0.5)
    env, log = simpy.Environment(), SimLog()
    crew = simpy.PriorityResource(env, capacity=1)
    bufs = [simpy.Store(env) for _ in range(3)]
    for b in bufs[:2]:
        for _ in range(200):
            b.put(SubLot(0, "p", "f", 100))
    ms = [
        Machine(
            env,
            f"m{i}",
            100,
            bufs[i],
            bufs[2],
            log,
            clocks=RunClocks(f, None, 5, 0, f"m{i}"),
            repair_crew=crew,
        )
        for i in range(2)
    ]
    env.run(until=150)
    for m in ms:
        m.rec.close()
    waits = sum(state_minutes(log, m.name).get("WAIT_STAFF", 0) for m in ms)
    assert waits > 0  # with one mechanic and two failing machines, someone waits

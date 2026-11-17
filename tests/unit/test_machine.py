import pytest
import simpy
from simhelpers import serial_line, state_minutes

from ffdt.sim.core import Calendar, SimLog, State, StateRecorder


def close_all(machines):
    for m in machines:
        m.rec.close()


def test_state_intervals_contiguous_and_sum_to_sim_time():
    env, log, ms, packed, done, _ = serial_line([300, 200, 250], 200)
    env.run(until=done)
    close_all(ms)
    for m in ms:
        iv = sorted((a, b) for st, _u, _s, a, b in log.states if st == m.name)
        assert iv[0][0] == 0
        for (_a0, b0), (a1, _b1) in zip(iv, iv[1:], strict=False):
            assert b0 == pytest.approx(a1)  # contiguous, non-overlapping
        assert sum(b - a for a, b in iv) == pytest.approx(env.now)


def test_buffer_occupancy_never_exceeds_capacity():
    env, log, ms, packed, done, bufs = serial_line([400, 100], 300, buffer_sublots=5)
    peak = [0]

    def monitor():
        while True:
            peak[0] = max(peak[0], len(bufs[1].items))
            yield env.timeout(0.05)

    env.process(monitor())
    env.run(until=done)
    assert 0 < peak[0] <= 5


def test_no_failure_throughput_equals_slowest_rate():
    env, log, ms, packed, done, _ = serial_line([300, 200], 1000)
    env.run(until=done)
    vials = sum(i.vials for _t, i in packed)
    rate = vials / (env.now - 100 / 300)  # exclude first-item pipeline fill
    assert rate == pytest.approx(200, rel=1e-3)


def test_starvation_and_blocking_classified():
    # slow upstream: downstream is starved about 2/3 of the time
    env, log, ms, _p, done, _ = serial_line([100, 300], 300)
    env.run(until=done)
    close_all(ms)
    down = state_minutes(log, "m1")
    assert down["STARVED"] / env.now == pytest.approx(2 / 3, abs=0.01)
    assert "BLOCKED" not in state_minutes(log, "m0")
    # fast upstream, slow downstream: upstream is blocked about 2/3 of the time
    env, log, ms, _p, done, _ = serial_line([300, 100], 300)
    env.run(until=done)
    close_all(ms)
    up = state_minutes(log, "m0")
    # upstream runs 300 x 1/3 = 100 min; once its 300th sub-lot is released it is starved
    # (source empty) while downstream drains the buffer (10 sub-lots + 1 in process = 11 min).
    assert up["RUN"] == pytest.approx(100)
    assert up["STARVED"] == pytest.approx(11, abs=0.5)
    assert up["BLOCKED"] == pytest.approx(env.now - 100 - up["STARVED"])
    assert up["BLOCKED"] / env.now > 0.6
    assert state_minutes(log, "m1").get("STARVED", 0) < 1.0


def test_vials_conserved_through_line():
    env, log, ms, packed, done, _ = serial_line([300, 200, 250], 123, vials=97)
    env.run(until=done)
    assert sum(i.vials for _t, i in packed) == 123 * 97


def test_recorder_skips_zero_length_intervals():
    env, log = simpy.Environment(), SimLog()
    r = StateRecorder(env, log, "x")
    r.set(State.STARVED)
    r.set(State.RUN)
    env.run(until=5)
    r.close()
    assert log.states == [("x", 0, "RUN", 0, 5)]


def test_calendar_windows():
    cal = Calendar(days=5, shifts_per_day=2, shift_min=480, break_min=60)
    assert cal.on_minutes(0, Calendar.WEEK) == pytest.approx(5 * 2 * 420)
    assert cal.on_minutes(Calendar.WEEK, 2 * Calendar.WEEK) == pytest.approx(4200)
    assert cal.is_on(0) and not cal.is_on(210) and cal.is_on(270)  # break 210-270
    assert not cal.is_on(960)  # after 2 shifts
    assert cal.next_change(900) == pytest.approx(960)  # end of shift 2
    assert cal.next_change(970) == pytest.approx(1440)  # next day start
    assert cal.next_change(4 * 1440 + 961) == pytest.approx(Calendar.WEEK)  # Fri night -> Mon


def test_calendar_pauses_work_as_planned_stop():
    cal = Calendar(days=5, shifts_per_day=1, shift_min=480, break_min=0)
    env, log, ms, packed, done, _ = serial_line([1], 6, vials=100, calendar=cal)
    env.run(until=done)  # 600 run minutes > one 480-min shift
    close_all(ms)
    st = state_minutes(log, "m0")
    assert st["RUN"] == pytest.approx(600)
    assert st["PLANNED_STOP"] == pytest.approx(1440 - 480)
    assert env.now == pytest.approx(1440 + 120)

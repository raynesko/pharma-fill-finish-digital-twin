"""Shared simulation building blocks: states, the state/event log, the shift calendar, entities.

Time unit: minutes. The log holds plain tuples so ``ffdt.metrics`` can consume it without
importing ``ffdt.sim``.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field
from enum import StrEnum

import simpy

EPS = 1e-9


class State(StrEnum):
    """Station states; names fixed by docs/domain/glossary.md section 1."""

    RUN = "RUN"
    STARVED = "STARVED"
    BLOCKED = "BLOCKED"
    DOWN = "DOWN"
    MINOR_STOP = "MINOR_STOP"
    CHANGEOVER = "CHANGEOVER"
    PLANNED_STOP = "PLANNED_STOP"
    WAIT_STAFF = "WAIT_STAFF"


@dataclass
class SimLog:
    """Append-only records produced by a run.

    states:  (station, unit, state, start_min, end_min)
    outputs: (station, unit, time_min, batch_id, vials_in, vials_out)
    events:  (time_min, kind, station, detail)   e.g. breakdowns, changeovers
    queues:  (buffer, time_min, delta, uid, vials)  delta +1 on entry, -1 on exit
    flow:    (time_min, kind, batch_id, vials)       kind: started / packed / scrapped
    """

    states: list[tuple] = field(default_factory=list)
    outputs: list[tuple] = field(default_factory=list)
    events: list[tuple] = field(default_factory=list)
    queues: list[tuple] = field(default_factory=list)
    flow: list[tuple] = field(default_factory=list)


class MonitoredStore(simpy.Store):
    """``simpy.Store`` that logs every entry and exit (for queue length, time in queue and
    Little's Law checks in ``ffdt.metrics``)."""

    def __init__(self, env, name: str, log: SimLog, capacity=math.inf):
        super().__init__(env, capacity=capacity)
        self.name, self._qlog = name, log.queues

    def _do_put(self, event):
        n = len(self.items)
        r = super()._do_put(event)
        if len(self.items) > n:
            self._qlog.append((self.name, self._env.now, 1, event.item.uid, event.item.vials))
        return r

    def _do_get(self, event):
        n = len(self.items)
        r = super()._do_get(event)
        if len(self.items) < n:
            v = event.value
            self._qlog.append((self.name, self._env.now, -1, v.uid, v.vials))
        return r


class StateRecorder:
    """Keeps one station unit's state as contiguous, non-overlapping intervals."""

    def __init__(self, env, log: SimLog, station: str, unit: int = 0):
        self.env, self.log, self.station, self.unit = env, log, station, unit
        self.state: State | None = None
        self.since = env.now

    def set(self, state: State) -> None:
        if state == self.state:
            return
        self._flush()
        self.state, self.since = state, self.env.now

    def _flush(self) -> None:
        now = self.env.now
        if self.state is not None and now > self.since + EPS:
            self.log.states.append((self.station, self.unit, str(self.state), self.since, now))
        self.since = now

    def close(self) -> None:
        """Write the open interval up to the current time (call once at end of run)."""
        self._flush()


class Calendar:
    """Repeating weekly shift calendar (A-023).

    Working days are the first ``days`` of each 7-day week. Shifts run back to back from 00:00;
    each shift has one break of ``break_min`` centered in the shift.
    """

    DAY = 1440.0
    WEEK = 7 * DAY

    def __init__(self, days: int, shifts_per_day: int, shift_min: float, break_min: float):
        if shifts_per_day * shift_min > self.DAY:
            raise ValueError("shifts exceed one day")
        windows = []  # on-windows within one week, sorted
        for d in range(days):
            for s in range(shifts_per_day):
                start = d * self.DAY + s * shift_min
                if break_min > 0:
                    b0 = start + (shift_min - break_min) / 2
                    windows += [(start, b0), (b0 + break_min, start + shift_min)]
                else:
                    windows.append((start, start + shift_min))
        self.windows = windows

    @classmethod
    def always_on(cls) -> Calendar:
        cal = cls.__new__(cls)
        cal.windows = [(0.0, cls.WEEK)]
        return cal

    def _locate(self, t: float):
        week = math.floor((t + EPS) / self.WEEK)
        return week, t - week * self.WEEK

    def is_on(self, t: float) -> bool:
        _, r = self._locate(t)
        return any(a - EPS <= r < b - EPS for a, b in self.windows)

    def next_change(self, t: float) -> float:
        """Absolute time of the next on/off transition strictly after ``t``."""
        week, r = self._locate(t)
        base = week * self.WEEK
        for a, b in self.windows:
            if a - EPS <= r < b - EPS:
                return base + b
            if r < a - EPS:
                return base + a
        if self.windows == [(0.0, self.WEEK)]:
            return base + 2 * self.WEEK  # always on
        return base + self.WEEK + self.windows[0][0]

    def off_intervals(self, t0: float, t1: float) -> list[tuple[float, float]]:
        """Off-shift intervals intersected with [t0, t1), in order."""
        out, t = [], t0
        while t < t1 - EPS:
            nxt = min(self.next_change(t), t1)
            if not self.is_on(t):
                out.append((t, nxt))
            t = nxt
        return out

    def on_minutes(self, t0: float, t1: float) -> float:
        """On-shift minutes in [t0, t1)."""
        total, t = 0.0, t0
        while t < t1 - EPS:
            nxt = min(self.next_change(t), t1)
            if self.is_on(t):
                total += nxt - t
            t = nxt
        return total


_ids = itertools.count()


@dataclass
class SubLot:
    """A group of vials moving together (ADR-001). ``defects`` are true rejectable defects
    carried hidden inside the sub-lot until inspection."""

    batch_id: int
    product: str
    format: str
    vials: int
    defects: int = 0
    last_in_batch: bool = False
    rework: bool = False  # vials returned from manual re-inspection (A-017, A-025)
    uid: int = field(default_factory=lambda: next(_ids))

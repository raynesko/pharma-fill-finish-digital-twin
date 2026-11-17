"""Machine process with finite buffers, state log, calendar, failures and hooks (T3.1.3).

A unit loops: wait for a sub-lot (STARVED) -> process at ``rate_vpm`` (RUN, interrupted by
breakdowns / minor stops / off-shift) -> optional transform (e.g. inspection) -> put downstream
(BLOCKED while the output buffer is full) -> optional end-of-batch hook (changeover).

Time unit: minutes. Rate unit: vials per minute.
"""

from __future__ import annotations

from collections.abc import Callable, Generator

import simpy

from ffdt.sim.core import EPS, Calendar, SimLog, State, StateRecorder, SubLot
from ffdt.sim.failures import RunClocks, Stop
from ffdt.sim.staffing import PRIORITY

# hooks
Transform = Callable[["Machine", SubLot], SubLot | None]
AfterBatch = Callable[["Machine", SubLot], Generator]


class Machine:
    def __init__(
        self,
        env: simpy.Environment,
        name: str,
        rate_vpm: float,
        inbuf: simpy.Store,
        outbuf: simpy.Store,
        log: SimLog,
        unit: int = 0,
        calendar: Calendar | None = None,
        clocks: RunClocks | None = None,
        transform: Transform | None = None,
        after_batch: AfterBatch | None = None,
        repair_crew: simpy.PriorityResource | None = None,
        before_item: AfterBatch | None = None,
    ):
        if rate_vpm <= 0:
            raise ValueError("rate_vpm must be > 0")
        self.env, self.name, self.unit = env, name, unit
        self.rate_vpm = rate_vpm
        self.inbuf, self.outbuf, self.log = inbuf, outbuf, log
        self.calendar = calendar or Calendar.always_on()
        self.clocks = clocks
        self.transform = transform
        self.after_batch = after_batch
        self.repair_crew = repair_crew
        self.before_item = before_item
        self.setup: tuple[str, str] | None = None  # (product, format) the unit is set up for
        self.rec = StateRecorder(env, log, name, unit)
        self.holding: SubLot | None = None  # sub-lot inside the machine (for WIP accounting)
        self.last_batch: SubLot | None = None
        self.process = env.process(self.run())

    # -- main loop ---------------------------------------------------------------------------
    def run(self):
        while True:
            self.rec.set(State.STARVED)
            item = yield self.inbuf.get()
            self.holding = item
            if self.before_item:  # e.g. catch-up changeover on a parallel unit
                yield from self.before_item(self, item)
            yield from self.work(item.vials / self.rate_vpm)
            out = self.transform(self, item) if self.transform else item
            vials_out = out.vials if out is not None else 0
            self.log.outputs.append(
                (self.name, self.unit, self.env.now, item.batch_id, item.vials, vials_out)
            )
            if out is not None and out.vials > 0:
                self.rec.set(State.BLOCKED)
                self.holding = out
                yield self.outbuf.put(out)
            self.holding = None
            self.last_batch = item
            if item.last_in_batch and self.after_batch:
                yield from self.after_batch(self, item)

    # -- timed activities --------------------------------------------------------------------
    def timed(self, duration: float, state: State):
        """Spend ``duration`` on-shift minutes in ``state``; off-shift time is PLANNED_STOP."""
        remaining = duration
        while remaining > EPS:
            now = self.env.now
            if not self.calendar.is_on(now):
                self.rec.set(State.PLANNED_STOP)
                yield self.env.timeout(self.calendar.next_change(now) - now)
                continue
            self.rec.set(state)
            step = min(remaining, self.calendar.next_change(now) - now)
            yield self.env.timeout(step)
            remaining -= step

    def work(self, duration: float):
        """Process for ``duration`` running minutes; failure clocks advance only here."""
        remaining = duration
        while remaining > EPS:
            now = self.env.now
            if not self.calendar.is_on(now):
                self.rec.set(State.PLANNED_STOP)
                yield self.env.timeout(self.calendar.next_change(now) - now)
                continue
            self.rec.set(State.RUN)
            step = min(remaining, self.calendar.next_change(now) - now)
            if self.clocks:
                step = min(step, self.clocks.next_in())
            yield self.env.timeout(step)
            remaining -= step
            if self.clocks:
                stop = self.clocks.advance(step)
                if stop is Stop.BREAKDOWN:
                    yield from self.breakdown()
                elif stop is Stop.MINOR:
                    self.log.events.append((self.env.now, "minor_stop", self.name, self.unit))
                    yield from self.timed(self.clocks.minor_min(), State.MINOR_STOP)

    def breakdown(self):
        self.log.events.append((self.env.now, "breakdown", self.name, self.unit))
        repair = self.clocks.repair_min()
        if self.repair_crew is None:
            yield from self.timed(repair, State.DOWN)
            return
        self.rec.set(State.WAIT_STAFF)
        with self.repair_crew.request(priority=PRIORITY["repair"]) as req:  # A-018
            yield req
            yield from self.timed(repair, State.DOWN)

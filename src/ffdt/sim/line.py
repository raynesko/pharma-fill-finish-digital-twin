"""Assemble a fill-finish line from a validated ``LineConfig`` (T3.1.5).

Flow: supply -> stations in config order (finite buffers between them) -> sink. Station names
are never hard-coded here; behavior comes from ``kind`` and config fields.

Accounting (vial conservation): every vial released by the supply is, at any instant, exactly one
of packed, scrapped, or WIP (supply queue, buffers, machines, tunnel belt).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import simpy

from ffdt.config import LineConfig, Station
from ffdt.sim.batches import ChangeoverPolicy
from ffdt.sim.core import Calendar, MonitoredStore, SimLog, SubLot
from ffdt.sim.failures import RunClocks
from ffdt.sim.machine import Machine, UnitGroup
from ffdt.sim.qa_release import QARelease
from ffdt.sim.quality import QualityModel
from ffdt.sim.staffing import Crews


@dataclass
class BatchRecord:
    batch_id: int
    product: str
    format: str
    size_vials: int
    start_min: float | None = None  # first sub-lot taken by the first station
    end_min: float | None = None  # last vial packed or scrapped
    packed: int = 0
    scrapped: int = 0
    qa_queue_min: float | None = None  # wait for a free QA reviewer
    review_min: float | None = None  # batch-record review (elapsed)
    release_min: float | None = None  # QA release time (after any release-testing hold)

    @property
    def complete(self) -> bool:
        return self.packed + self.scrapped == self.size_vials

    @property
    def lead_time_min(self) -> float | None:
        """Batch lead time: first sub-lot started to QA release."""
        if self.release_min is None or self.start_min is None:
            return None
        return self.release_min - self.start_min


@dataclass
class Ledger:
    started: int = 0
    packed: int = 0
    scrapped: int = 0
    batches: list[BatchRecord] = field(default_factory=list)


class Tunnel:
    """Depyrogenation tunnel (A-007): a loading section at ``rate_vpm`` feeds a belt; each
    sub-lot exits ``residence_min`` after loading, in order. When the outlet is blocked the belt
    fills and the loading section reports BLOCKED (backpressure to the washer). No scrap."""

    def __init__(self, line: Line, st: Station, inbuf: simpy.Store, outbuf: simpy.Store):
        env = line.env
        self.residence = st.residence_min
        belt_cap = max(1, math.ceil(st.rate_vpm * st.residence_min / line.cfg.sublot_vials) - 1)
        self.belt = simpy.Store(env, capacity=belt_cap)
        self.at_exit: SubLot | None = None
        self.loader = line.make_machine(st, 0, inbuf, self.belt, transform=self._stamp)
        self.outbuf, self.env = outbuf, env
        env.process(self._exit())

    def _stamp(self, _m, item: SubLot) -> SubLot:
        item.ready_at = self.env.now + self.residence
        return item

    def _exit(self):
        while True:
            item = yield self.belt.get()
            self.at_exit = item
            yield self.env.timeout(max(0.0, item.ready_at - self.env.now))
            yield self.outbuf.put(item)
            self.at_exit = None

    def wip_items(self):
        return list(self.belt.items) + ([self.at_exit] if self.at_exit else [])


class Line:
    def __init__(
        self,
        cfg: LineConfig,
        root_seed: int = 0,
        replication: int = 0,
        use_calendar: bool = True,
        stochastic: bool = True,
        changeovers: bool = True,
        quality: bool = True,
        staffing: bool = True,
        qa: bool = True,
    ):
        """``stochastic=False`` removes failures and minor stops and uses modal changeover
        times. ``changeovers`` / ``quality`` / ``staffing`` switch those sub-models off for
        verification (``staffing=False``: repairs and changeovers never wait for staff)."""
        self.cfg, self.root_seed, self.replication = cfg, root_seed, replication
        self.stochastic, self.use_changeovers = stochastic, changeovers
        self.quality = QualityModel(self, cfg.quality, root_seed, replication) if quality else None
        self.fill_station = next(
            (s.name for s in cfg.stations if s.changeover_scope == "full"), None
        )
        self.env = env = simpy.Environment()
        self.crews = Crews.from_config(env, cfg.staffing) if staffing else None
        self.qa = QARelease(env, cfg.qa, root_seed, replication) if qa else None
        if self.qa:
            self.qa.expected = len(cfg.schedule)
        self.log = SimLog()
        self.ledger = Ledger()
        c = cfg.calendar
        self.calendar = (
            Calendar(c.days, c.shifts_per_day, c.shift_min, c.break_min_per_shift)
            if use_calendar
            else Calendar.always_on()
        )
        cap = cfg.buffer_vials // cfg.sublot_vials
        n = len(cfg.stations)
        log = self.log
        self.supply = MonitoredStore(env, f"in:{cfg.stations[0].name}", log, capacity=cap)
        self.buffers = {  # buffer *upstream* of station i, keyed by station name
            st.name: (
                self.supply if i == 0 else MonitoredStore(env, f"in:{st.name}", log, capacity=cap)
            )
            for i, st in enumerate(cfg.stations)
        }
        self.sink_buf = simpy.Store(env)
        # AVI rejects awaiting manual re-inspection
        self.reject_store = MonitoredStore(env, "in:manual_inspection", log)
        self.machines: list[Machine] = []
        self.tunnels: list[Tunnel] = []
        for i, st in enumerate(cfg.stations):
            inbuf = self.buffers[st.name]
            outbuf = self.sink_buf if i == n - 1 else self.buffers[cfg.stations[i + 1].name]
            if st.kind == "tunnel":
                self.tunnels.append(Tunnel(self, st, inbuf, outbuf))
            else:
                group = UnitGroup(env) if st.count > 1 else None
                for u in range(st.count):
                    self.make_machine(st, u, inbuf, outbuf, group=group)
        if self.quality:
            self.quality.reject_store = self.reject_store
            insp = next(i for i, s in enumerate(cfg.stations) if s.kind == "inspection")
            rework_to = (
                self.sink_buf if insp == n - 1 else self.buffers[cfg.stations[insp + 1].name]
            )
            for u in range(cfg.staffing.inspector):  # offline pool, one unit per inspector
                self.machines.append(
                    Machine(
                        env,
                        "manual_inspection",
                        cfg.quality.manual_rate_vpm_per_inspector,
                        self.reject_store,
                        rework_to,
                        self.log,
                        unit=u,
                        calendar=self.calendar,
                        transform=self.quality.manual,
                    )
                )
        self.first_station = cfg.stations[0].name
        self.done = env.event()
        env.process(self._source())
        env.process(self._sink())

    # -- construction helpers ----------------------------------------------------------------
    def make_machine(self, st: Station, unit, inbuf, outbuf, transform=None, group=None) -> Machine:
        clocks = None
        if self.stochastic and (st.failures or st.minor_stops):
            clocks = RunClocks(
                st.failures, st.minor_stops, self.root_seed, self.replication, f"{st.name}#{unit}"
            )
        if transform is None and self.quality:
            if st.name == self.fill_station:
                transform = self.quality.fill
            elif st.kind == "inspection":
                transform = self.quality.avi
        policy = None
        if self.use_changeovers and st.changeover_scope != "none":
            policy = ChangeoverPolicy(
                st.name,
                unit,
                st.changeover_scope,
                self.cfg.changeovers,
                self.cfg.schedule,
                self.root_seed,
                self.replication,
                stochastic=self.stochastic,
                crew=self.crews.operator if self.crews else None,
            )
        m = Machine(
            self.env,
            st.name,
            st.rate_vpm,
            inbuf,
            outbuf,
            self.log,
            unit=unit,
            calendar=self.calendar,
            clocks=clocks,
            transform=transform,
            after_batch=policy.after_batch if policy else None,
            before_item=policy.before_item if policy else None,
            repair_crew=self.crews.mechanic if self.crews else None,
            group=group,
        )
        self.machines.append(m)
        return m

    # -- flow --------------------------------------------------------------------------------
    def _source(self):
        """Infinite upstream supply (A-004): releases the schedule as sub-lots, in order."""
        n = self.cfg.sublot_vials
        for b_id, b in enumerate(self.cfg.schedule):
            rec = BatchRecord(b_id, b.product, b.format, b.size_vials)
            self.ledger.batches.append(rec)
            sizes = [n] * (b.size_vials // n) + ([b.size_vials % n] if b.size_vials % n else [])
            for k, v in enumerate(sizes):
                item = SubLot(b_id, b.product, b.format, v, last_in_batch=(k == len(sizes) - 1))
                yield self.supply.put(item)
                self.ledger.started += v
                self.log.flow.append((self.env.now, "started", b_id, v))
                if rec.start_min is None:
                    rec.start_min = self.env.now

    def _sink(self):
        while True:
            item = yield self.sink_buf.get()
            self.ledger.packed += item.vials
            self.log.flow.append((self.env.now, "packed", item.batch_id, item.vials))
            rec = self.ledger.batches[item.batch_id]
            rec.packed += item.vials
            if self.quality:
                self.quality.packed(item)
            self._check_batch(rec)

    def scrap(self, item: SubLot, vials: int) -> None:
        """Called by quality logic when vials leave the flow as scrap."""
        self.ledger.scrapped += vials
        self.log.flow.append((self.env.now, "scrapped", item.batch_id, vials))
        rec = self.ledger.batches[item.batch_id]
        rec.scrapped += vials
        self._check_batch(rec)

    def _check_batch(self, rec: BatchRecord) -> None:
        if rec.complete and rec.end_min is None:
            rec.end_min = self.env.now
            self.log.events.append((self.env.now, "batch_complete", "line", rec.batch_id))
            if self.qa:
                self.qa.submit(rec)
            if all(b.complete for b in self.ledger.batches) and len(self.ledger.batches) == len(
                self.cfg.schedule
            ):
                self.done.succeed()

    # -- accounting --------------------------------------------------------------------------
    def wip_vials(self) -> int:
        items = list(self.supply.items)
        for buf in self.buffers.values():
            if buf is not self.supply:
                items += buf.items
        items += self.sink_buf.items + self.reject_store.items
        items += [m.holding for m in self.machines if m.holding is not None]
        for t in self.tunnels:
            items += t.wip_items()
        return sum(i.vials for i in items)

    def run(self, max_min: float = 4 * Calendar.WEEK) -> bool:
        """Run until every batch is packed (terminating campaign, A-020) or ``max_min``.
        Returns True if the campaign completed.

        Station state logs are closed at that moment (``campaign_end_min``). QA review then
        continues off-line until every batch is released, so lead times exist without
        stretching any station's state log (D5)."""
        stop = self.env.any_of([self.done, self.env.timeout(max_min)])
        self.env.run(until=stop)
        self.campaign_end_min = self.env.now
        for m in self.machines:
            m.rec.close()
            m.rec.state = None  # nothing after campaign end is equipment time
        if self.done.triggered and self.qa:
            self.env.run(until=self.qa.all_released)
        return self.done.triggered

    # -- export (plain data for ffdt.metrics; no sim objects) ----------------------------
    def export(self) -> dict:
        """Everything ``ffdt.metrics`` needs, as plain Python data. Call after ``run``."""
        end = self.campaign_end_min
        stations = [
            {"station": s.name, "rate_vpm": s.rate_vpm, "units": s.count} for s in self.cfg.stations
        ]
        if self.quality and self.cfg.staffing.inspector:
            stations.append(
                {
                    "station": "manual_inspection",
                    "rate_vpm": self.cfg.quality.manual_rate_vpm_per_inspector,
                    "units": self.cfg.staffing.inspector,
                    "offline": True,
                }
            )
        batches = [
            {
                "batch_id": b.batch_id,
                "product": b.product,
                "format": b.format,
                "size": b.size_vials,
                "start_min": b.start_min,
                "end_min": b.end_min,
                "packed": b.packed,
                "scrapped": b.scrapped,
                "qa_queue_min": b.qa_queue_min,
                "review_min": b.review_min,
                "release_min": b.release_min,
            }
            for b in self.ledger.batches
        ]
        q = self.quality.ledger if self.quality else None
        return {
            "config_name": self.cfg.name,
            "config_hash": self.cfg.hash(),
            "root_seed": self.root_seed,
            "replication": self.replication,
            "completed": self.done.triggered,
            "horizon_min": end,
            "off_shift": self.calendar.off_intervals(0.0, end),
            "stations": stations,
            "states": list(self.log.states),
            "outputs": list(self.log.outputs),
            "events": list(self.log.events),
            "queues": [r for r in self.log.queues if r[1] <= end],
            "flow": [r for r in self.log.flow if r[0] <= end],
            "batches": batches,
            "started": self.ledger.started,
            "packed": self.ledger.packed,
            "scrapped": self.ledger.scrapped,
            "scrap_by_cause": dict(q.scrapped) if q else {},
            "escapes": q.escapes if q else 0,
        }

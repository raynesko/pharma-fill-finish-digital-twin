"""Production schedule, changeover rules and the batch record table (T3.2.1, A-012, A-013).

Two schedule modes:
  fixed   the ``schedule`` list in the config, run in order (verification and all scenarios)
  seeded  ``generate_schedule`` draws a product/format sequence from a named stream

Changeovers are rolling (A-013): each station unit changes over as soon as it finishes the last
sub-lot of a batch, to the setup of the next scheduled batch. The type depends on what changes
and on the station's ``changeover_scope`` (A-012). A unit that receives a sub-lot it is not set
up for (a parallel unit that did not process the batch's last sub-lot) changes over first.
Rework lots returned from manual re-inspection never trigger a changeover (A-025).
"""

from __future__ import annotations

from enum import StrEnum

import pandas as pd

from ffdt import params as P
from ffdt.config import Batch, Changeovers
from ffdt.rng import stream
from ffdt.sim.core import State
from ffdt.sim.staffing import PRIORITY


class CO(StrEnum):
    NONE = "none"
    SAME_PRODUCT = "same_product"
    FORMAT_CHANGE = "format_change"
    PRODUCT_CHANGE = "product_change"


def changeover_type(prev: tuple[str, str] | None, nxt: tuple[str, str], scope: str) -> CO:
    """Changeover needed between batch setups ``(product, format)`` for a station ``scope``.

    ``prev is None`` means the unit has not been set up yet (start of campaign): no changeover.
    Identical setups return SAME_PRODUCT for ``full``/``packaging`` (line clearance between
    batches); ``ChangeoverPolicy`` applies that only at a batch boundary.
    """
    if prev is None or scope == "none":
        return CO.NONE
    product_differs, format_differs = prev[0] != nxt[0], prev[1] != nxt[1]
    if scope == "full":
        if product_differs:
            return CO.PRODUCT_CHANGE  # product + format change takes the product-change time
        return CO.FORMAT_CHANGE if format_differs else CO.SAME_PRODUCT
    if scope == "packaging":
        return CO.FORMAT_CHANGE if format_differs else CO.SAME_PRODUCT
    if scope == "glass":
        return CO.FORMAT_CHANGE if format_differs else CO.NONE
    raise ValueError(f"unknown changeover scope {scope!r}")


def generate_schedule(
    products: list[str],
    formats: list[str],
    n_batches: int,
    size_vials: int,
    root_seed: int,
    replication: int = 0,
) -> list[Batch]:
    """Seeded mode: uniform random product and format per batch."""
    rng = stream(root_seed, replication, "schedule")
    return [
        Batch(
            product=str(rng.choice(products)),
            format=str(rng.choice(formats)),
            size_vials=size_vials,
        )
        for _ in range(n_batches)
    ]


class ChangeoverPolicy:
    """Per station unit. Supplies Machine's ``after_batch`` and ``before_item`` hooks."""

    def __init__(
        self,
        station: str,
        unit: int,
        scope: str,
        changeovers: Changeovers,
        schedule: list[Batch],
        root_seed: int,
        replication: int,
        stochastic: bool = True,
        crew=None,  # simpy.PriorityResource of line operators (wired in T3.2.3)
    ):
        self.scope, self.schedule, self.crew = scope, schedule, crew
        self.stochastic = stochastic
        self.dists = {
            co: P.scaled(P.triangular(t.low_min, t.mode_min, t.high_min), changeovers.scale)
            for co, t in (
                (CO.SAME_PRODUCT, changeovers.same_product),
                (CO.FORMAT_CHANGE, changeovers.format_change),
                (CO.PRODUCT_CHANGE, changeovers.product_change),
            )
        }
        self.rng = stream(root_seed, replication, f"{station}#{unit}.changeover")

    def duration(self, co: CO) -> float:
        d = self.dists[co]
        return float(d.sample(self.rng)) if self.stochastic else d.params[1] * 1.0  # mode

    def after_batch(self, m, item):
        nxt = item.batch_id + 1
        if nxt < len(self.schedule):
            b = self.schedule[nxt]
            yield from self._change(m, (b.product, b.format), nxt, between_batches=True)

    def before_item(self, m, item):
        target = (item.product, item.format)
        if item.rework or m.setup == target:
            return
        if m.setup is None:  # campaign start: line is set up for the first batch
            m.setup = target
            return
        yield from self._change(m, target, item.batch_id, between_batches=False)

    def _change(self, m, target, to_batch: int, between_batches: bool):
        co = changeover_type(m.setup, target, self.scope)
        m.setup = target
        if co is CO.NONE or (co is CO.SAME_PRODUCT and not between_batches):
            return
        dur = self.duration(co)
        m.log.events.append((m.env.now, "changeover", m.name, (m.unit, str(co), to_batch, dur)))
        if self.crew is None:
            yield from m.timed(dur, State.CHANGEOVER)
            return
        m.rec.set(State.WAIT_STAFF)
        with self.crew.request(priority=PRIORITY["changeover"]) as req:  # A-018
            yield req
            yield from m.timed(dur, State.CHANGEOVER)


def batch_table(ledger) -> pd.DataFrame:
    """Batch record table: one row per scheduled batch. Times in minutes from campaign start;
    yield = packed / size (good vials over vials started)."""
    rows = [
        {
            "batch_id": b.batch_id,
            "product": b.product,
            "format": b.format,
            "size": b.size_vials,
            "start_min": b.start_min,
            "end_min": b.end_min,
            "packed": b.packed,
            "scrapped": b.scrapped,
            "yield": b.packed / b.size_vials,
            "qa_queue_min": b.qa_queue_min,
            "review_min": b.review_min,
            "release_min": b.release_min,
            "lead_time_min": b.lead_time_min,
        }
        for b in ledger.batches
    ]
    return pd.DataFrame(rows)

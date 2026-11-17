"""Staff pools by role (T3.2.3, A-005, A-018, A-024).

  mechanic   repairs after a breakdown             priority 0 (highest)
  operator   changeovers and line clearance        priority 1
  inspector  manual re-inspection of AVI rejects   priority 2 (lowest)

Each role is its own ``simpy.PriorityResource`` sized from ``staffing`` in the config (scenario
YAML can override it). A station that needs staff and finds none free logs ``WAIT_STAFF`` until
one is granted. Priorities decide the order when requests queue for the *same* pool; they are
also exported so a scenario that merges roles (``Crews.shared``) keeps the A-018 order.

Inspectors are modeled as the units of the offline ``manual_inspection`` station (one unit per
inspector, see ``ffdt.sim.line``), so re-inspection waits in the reject queue rather than as
``WAIT_STAFF`` on a line station. Minor stoppages need no staff (A-024). Staff work the shift
calendar like the line (A-005, A-023).

With 0 staff in a role, the dependent activity never starts; the campaign then cannot finish,
which ``Line.run`` reports by returning False at ``max_min``.
"""

from __future__ import annotations

from dataclasses import dataclass

import simpy

from ffdt.config import Staffing

PRIORITY = {"repair": 0, "changeover": 1, "reinspection": 2}


class _ZeroCapacity:
    """Stand-in for a pool of size 0: requests are never granted."""

    def __init__(self, env):
        self.env = env

    def request(self, priority=0):
        return _NeverGranted(self.env)


class _NeverGranted:
    def __init__(self, env):
        self.event = env.event()

    def __enter__(self):
        return self.event

    def __exit__(self, *exc):
        return False


@dataclass
class Crews:
    mechanic: object
    operator: object
    inspector_count: int

    @classmethod
    def from_config(cls, env: simpy.Environment, s: Staffing) -> Crews:
        return cls(_pool(env, s.mechanic), _pool(env, s.operator), s.inspector)

    @classmethod
    def shared(cls, env: simpy.Environment, size: int, inspectors: int) -> Crews:
        """One pool doing both repairs and changeovers (cross-trained crew)."""
        pool = _pool(env, size)
        return cls(pool, pool, inspectors)


def _pool(env, n: int):
    return simpy.PriorityResource(env, capacity=n) if n > 0 else _ZeroCapacity(env)

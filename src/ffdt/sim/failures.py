"""Operation-dependent breakdowns and minor stoppages (T3.1.4, A-002, A-016, A-035..A-037).

Two independent clocks count down **running time only**. When one expires the machine leaves
``RUN``: a breakdown needs a repair (and a mechanic once staffing is wired), a minor stoppage
is cleared by the operator. Each clock and each duration draws from its own named stream so
scenarios keep common random numbers.
"""

from __future__ import annotations

import math
from enum import Enum

from ffdt import params as P
from ffdt.config import Failures, MinorStops
from ffdt.rng import stream
from ffdt.sim.core import EPS


class Stop(Enum):
    BREAKDOWN = "breakdown"
    MINOR = "minor"


class RunClocks:
    def __init__(
        self,
        failures: Failures | None,
        minor: MinorStops | None,
        root_seed: int,
        replication: int,
        key: str,
        mtbf_scale: float = 1.0,
        mttr_scale: float = 1.0,
    ):
        def rng(purpose):
            return stream(root_seed, replication, f"{key}.{purpose}")

        self._ttf_d = self._rep_d = self._between_d = self._dur_d = None
        if failures:
            self._ttf_d = P.exponential_from_mean(failures.mtbf_min * mtbf_scale)
            self._rep_d = P.lognormal_from_mean_cv(
                failures.mttr_mean_min * mttr_scale, failures.mttr_cv
            )
            self._ttf_rng, self._rep_rng = rng("ttf"), rng("repair")
        if minor:
            self._between_d = P.exponential_from_mean(minor.mean_between_min)
            self._dur_d = P.exponential_from_mean(minor.mean_duration_min)
            self._between_rng, self._dur_rng = rng("minor_between"), rng("minor_duration")
        self.ttf = self._draw_ttf()
        self.ttm = self._draw_minor()

    def _draw_ttf(self) -> float:
        return float(self._ttf_d.sample(self._ttf_rng)) if self._ttf_d else math.inf

    def _draw_minor(self) -> float:
        return float(self._between_d.sample(self._between_rng)) if self._between_d else math.inf

    def next_in(self) -> float:
        """Running minutes until the next stop."""
        return min(self.ttf, self.ttm)

    def advance(self, run_min: float) -> Stop | None:
        """Consume ``run_min`` of running time; return the stop that is now due, if any."""
        self.ttf -= run_min
        self.ttm -= run_min
        if self.ttf <= EPS:
            self.ttf = self._draw_ttf()
            return Stop.BREAKDOWN
        if self.ttm <= EPS:
            self.ttm = self._draw_minor()
            return Stop.MINOR
        return None

    def repair_min(self) -> float:
        return float(self._rep_d.sample(self._rep_rng))

    def minor_min(self) -> float:
        return float(self._dur_d.sample(self._dur_rng))

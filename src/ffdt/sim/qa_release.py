"""QA hold and batch release (T3.2.4, A-042, glossary D5).

When the last vial of a batch is packed, the batch joins a FIFO queue for ``qa.reviewers``
reviewers. Batch-record review (21 CFR 211.192) takes a shifted-lognormal *elapsed* time
(minimum effort ``review_min_min`` plus right-skewed backlog delay, overall mean
``review_mean_min``, ``review_cv`` = CV of the excess over the minimum). After review the batch
waits a fixed ``release_hold_min`` for release testing. The default hold is 0: the 14-day
sterility-test incubation (USP <71>) is NOT verified here and is excluded (B-029, open question).

QA never touches the line: it runs after packing, draws from its own stream ``qa.review`` and
does not change any station state, so equipment OEE is identical with or without it (D5).
"""

from __future__ import annotations

import simpy

from ffdt import params as P
from ffdt.config import QA
from ffdt.rng import stream


class QARelease:
    def __init__(self, env: simpy.Environment, qa: QA, root_seed: int, replication: int):
        self.env, self.qa = env, qa
        self.reviewers = simpy.Resource(env, capacity=qa.reviewers)
        self.dist = P.shifted_lognormal(qa.review_min_min, qa.review_mean_min, qa.review_cv)
        self.rng = stream(root_seed, replication, "qa.review")
        self.released = 0
        self.expected = 0  # number of scheduled batches; set by Line
        self.all_released = env.event()

    def submit(self, rec) -> None:
        self.env.process(self._release(rec))

    def _release(self, rec):
        t0 = self.env.now
        with self.reviewers.request() as req:
            yield req
            rec.qa_queue_min = self.env.now - t0
            rec.review_min = float(self.dist.sample(self.rng))
            yield self.env.timeout(rec.review_min)
        yield self.env.timeout(self.qa.release_hold_min)
        rec.release_min = self.env.now
        self.released += 1
        if self.released == self.expected:
            self.all_released.succeed()

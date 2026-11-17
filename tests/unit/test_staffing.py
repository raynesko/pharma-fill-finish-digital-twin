from pathlib import Path

import pytest
import simpy
from simhelpers import state_minutes

from ffdt.config import apply_overrides, load_config
from ffdt.sim.line import Line
from ffdt.sim.staffing import PRIORITY, Crews

BASE = Path(__file__).resolve().parents[2] / "configs" / "baseline_line.yaml"
FRAGILE = {"mtbf_min": 120, "mttr_mean_min": 30, "mttr_cv": 0.5}
SHORT = [
    {"product": "prod_a", "format": "vial_2r", "size_vials": 20_000},
    {"product": "prod_b", "format": "vial_10r", "size_vials": 20_000},
]


@pytest.fixture(scope="module")
def cfg():
    return load_config(BASE)


def _fragile(cfg, **staffing):
    over = {
        "schedule": SHORT,
        "station_overrides": {s.name: {"failures": FRAGILE} for s in cfg.stations},
    }
    if staffing:
        over["staffing"] = staffing
    return apply_overrides(cfg, over)


def _wait(line):
    return sum(b - a for _st, _u, s, a, b in line.log.states if s == "WAIT_STAFF")


def test_no_mechanic_means_repairs_never_start(cfg):
    line = Line(_fragile(cfg, operator=4, mechanic=0, inspector=2), root_seed=1)
    assert not line.run(max_min=3 * 1440)
    breakdowns = [e for e in line.log.events if e[1] == "breakdown"]
    assert breakdowns
    assert all(state_minutes(line.log, s.name).get("DOWN", 0) == 0 for s in cfg.stations)
    assert _wait(line) > 0


def test_no_operator_means_changeovers_never_start(cfg):
    c = apply_overrides(cfg, {"schedule": SHORT, "staffing": {"operator": 0}})
    line = Line(c, root_seed=1, stochastic=False, quality=False)
    assert not line.run(max_min=3 * 1440)
    assert all(state_minutes(line.log, s.name).get("CHANGEOVER", 0) == 0 for s in c.stations)
    assert line.ledger.batches[0].complete and not line.ledger.batches[1].complete
    assert state_minutes(line.log, "filler")["WAIT_STAFF"] > 0


def test_no_inspector_means_rejects_wait(cfg):
    c = apply_overrides(cfg, {"schedule": SHORT, "staffing": {"inspector": 0}})
    line = Line(c, root_seed=1, stochastic=False, changeovers=False)
    assert not line.run(max_min=3 * 1440)
    assert line.reject_store.items  # rejects never re-inspected
    assert "manual_inspection" not in {st for st, *_ in line.log.states}


def test_more_mechanics_less_wait_for_staff(cfg):
    one = Line(_fragile(cfg, operator=4, mechanic=1, inspector=2), root_seed=4)
    three = Line(_fragile(cfg, operator=4, mechanic=3, inspector=2), root_seed=4)
    assert one.run() and three.run()
    assert _wait(one) > _wait(three)


def test_staffing_overridable_by_scenario_yaml(cfg):
    c = apply_overrides(cfg, {"staffing": {"mechanic": 3, "operator": 6}})
    line = Line(c)
    assert line.crews.mechanic.capacity == 3 and line.crews.operator.capacity == 6


def test_priority_repair_before_changeover_before_reinspection():
    assert PRIORITY["repair"] < PRIORITY["changeover"] < PRIORITY["reinspection"]
    env = simpy.Environment()
    crews = Crews.shared(env, size=1, inspectors=0)
    order = []

    def holder():
        with crews.operator.request(priority=0) as r:
            yield r
            yield env.timeout(10)

    def job(name, delay):
        yield env.timeout(delay)
        with crews.mechanic.request(priority=PRIORITY[name]) as r:
            yield r
            order.append(name)
            yield env.timeout(1)

    env.process(holder())
    env.process(job("reinspection", 1))  # queued first ...
    env.process(job("changeover", 2))
    env.process(job("repair", 3))  # ... but served first
    env.run()
    assert order == ["repair", "changeover", "reinspection"]

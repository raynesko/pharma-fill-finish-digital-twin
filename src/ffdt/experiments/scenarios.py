"""Pre-registered scenarios (T5.1.1 / T5.1.2).

Each ``configs/scenarios/*.yaml`` is a diff against frozen baseline v1.0:

    name: sc01_avi_plus1
    description: "..."
    family: SC-01
    exploratory: false       # true = not in the Holm-adjusted main set
    overrides: {...}         # ffdt.config.apply_overrides format

``run_all`` runs baseline and every scenario with the same seed and replication numbers (common
random numbers), writes ``results/<name>/<name>.<part>.parquet`` with config hash and git SHA in
the metadata, and appends one JSON line per run to ``results/run_log.jsonl``.

    python -m ffdt.experiments.scenarios          (or: python tasks.py scenarios)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml

from ffdt.config import LineConfig, apply_overrides, load_config
from ffdt.experiments import runner

ROOT = Path(__file__).resolve().parents[3]
SCENARIO_DIR = ROOT / "configs" / "scenarios"
BASELINE = ROOT / "configs" / "baseline_line.yaml"
RESULTS = ROOT / "results"
REQUIRED = {"name", "description", "family", "exploratory", "overrides"}


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    family: str
    exploratory: bool
    config: LineConfig
    path: Path | None


def baseline_scenario() -> Scenario:
    cfg = load_config(BASELINE)
    return Scenario("baseline", "Baseline v1.0", "BASE", False, cfg, BASELINE)


def load(path: Path, base: LineConfig | None = None) -> Scenario:
    with open(path, encoding="utf-8") as f:
        d = yaml.safe_load(f)
    if missing := REQUIRED - set(d):
        raise ValueError(f"{path.name}: missing keys {sorted(missing)}")
    if d["name"] != path.stem:
        raise ValueError(f"{path.name}: name {d['name']!r} must match the file name")
    base = base or load_config(BASELINE)
    cfg = apply_overrides(base, d["overrides"])
    cfg = cfg.model_copy(update={"name": d["name"]})
    return Scenario(d["name"], d["description"], d["family"], bool(d["exploratory"]), cfg, path)


def all_scenarios(directory: Path = SCENARIO_DIR) -> list[Scenario]:
    base = load_config(BASELINE)
    return [load(p, base) for p in sorted(directory.glob("*.yaml"))]


def run_all(
    n_reps: int | None = None,
    seed: int | None = None,
    n_jobs: int = -1,
    out_dir: Path = RESULTS,
    only: list[str] | None = None,
) -> list[dict]:
    exp = runner.load_experiment()
    n_reps = n_reps or exp["n_reps"]
    seed = exp["seed"] if seed is None else seed
    out_dir.mkdir(parents=True, exist_ok=True)
    log = []
    for sc in [baseline_scenario(), *all_scenarios()]:
        if only and sc.name not in only:
            continue
        t0 = time.perf_counter()
        res = runner.run(sc.config, n_reps=n_reps, seed=seed, n_jobs=n_jobs)
        runner.write_parquet(res, out_dir / sc.name / f"{sc.name}.parquet")
        entry = {
            "time_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "scenario": sc.name,
            "family": sc.family,
            "exploratory": sc.exploratory,
            "config_hash": sc.config.hash(),
            "seed": seed,
            "n_reps": n_reps,
            "completed_reps": int(res.summary["completed"].sum()),
            "seconds": round(time.perf_counter() - t0, 1),
            "git_sha": runner.git_sha(ROOT),
        }
        with open(out_dir / "run_log.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        print(
            f"{sc.name:28s} {entry['completed_reps']}/{n_reps} complete  {entry['seconds']:6.1f} s"
        )
        log.append(entry)
    return log


if __name__ == "__main__":
    run_all()

"""Seeded replications of a line configuration (T3.2.6).

Replication r of a config uses random streams keyed by (root_seed, r, stream name) (``ffdt.rng``),
so a station's draws do not depend on any other station's parameters, the station order or the
number of replications: scenarios compared at the same (seed, r) share common random numbers.

    res = run(cfg, n_reps=30, seed=20261116, n_jobs=-1)
    res.summary    one row per replication (ffdt.metrics.oee.summarize)
    res.stations   one row per replication x station (ffdt.metrics.oee.station_table)
    res.pareto     one row per replication x loss category
    res.queues     one row per replication x buffer (ffdt.metrics.ledger.queue_stats)
    write_parquet(res, "results/raw/baseline.parquet")
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from joblib import Parallel, delayed

from ffdt.config import LineConfig
from ffdt.metrics import ledger, oee
from ffdt.sim.line import Line

DEFAULT_SEED = 20261116  # fixed project seed; scenarios reuse it for common random numbers
EXPERIMENT_YAML = Path(__file__).resolve().parents[3] / "configs" / "experiment.yaml"


def load_experiment(path: str | Path = EXPERIMENT_YAML) -> dict:
    """Experiment design (seed, n_reps, CI target) chosen in T4.1.3; used by every later run."""
    import yaml

    with open(path, encoding="utf-8") as f:
        exp = yaml.safe_load(f)
    missing = {"seed", "n_reps", "ci_level", "rel_half_width_target"} - set(exp)
    if missing:
        raise ValueError(f"experiment.yaml missing {sorted(missing)}")
    return exp


@dataclass
class Results:
    config: LineConfig
    seed: int
    summary: pd.DataFrame
    stations: pd.DataFrame
    pareto: pd.DataFrame
    queues: pd.DataFrame


def run_replication(cfg: LineConfig, seed: int, rep: int, max_min: float | None = None) -> dict:
    line = Line(cfg, root_seed=seed, replication=rep)
    line.run() if max_min is None else line.run(max_min=max_min)
    exp = line.export()
    st = oee.station_table(exp)
    par = oee.loss_pareto(exp, st)
    return {
        "summary": oee.summarize(exp),
        "stations": st.assign(replication=rep),
        "pareto": par.assign(replication=rep),
        "queues": ledger.queue_stats(exp).assign(replication=rep),
    }


def run(cfg: LineConfig, n_reps: int, seed: int = DEFAULT_SEED, n_jobs: int = 1) -> Results:
    """Run replications 0..n_reps-1. ``n_jobs`` > 1 (or -1) runs them in parallel processes;
    results are identical to serial because each replication owns its streams."""
    if n_jobs == 1:
        outs = [run_replication(cfg, seed, r) for r in range(n_reps)]
    else:
        outs = Parallel(n_jobs=n_jobs)(
            delayed(run_replication)(cfg, seed, r) for r in range(n_reps)
        )
    return Results(
        config=cfg,
        seed=seed,
        summary=pd.DataFrame([o["summary"] for o in outs]),
        stations=pd.concat([o["stations"] for o in outs], ignore_index=True),
        pareto=pd.concat([o["pareto"] for o in outs], ignore_index=True),
        queues=pd.concat([o["queues"] for o in outs], ignore_index=True),
    )


def git_sha(cwd: Path | None = None) -> str:
    """Current commit, '+dirty' if the tree has changes, or 'no-git' outside a repository."""
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            cwd=cwd, capture_output=True, text=True, check=True,
        ).stdout.strip()  # fmt: skip
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=cwd, capture_output=True, text=True, check=True
        ).stdout.strip()
        return sha + ("+dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "no-git"


def metadata(res: Results) -> dict[str, str]:
    return {
        "ffdt.config_name": res.config.name,
        "ffdt.config_version": res.config.version,
        "ffdt.config_hash": res.config.hash(),
        "ffdt.seed": str(res.seed),
        "ffdt.n_reps": str(len(res.summary)),
        "ffdt.git_sha": git_sha(Path(__file__).resolve().parent),
        "ffdt.label": "SIMULATED, BENCHMARK-PARAMETERIZED. NOT PLANT DATA.",
        "ffdt.config_json": json.dumps(res.config.model_dump(mode="json"), sort_keys=True),
    }


def write_parquet(res: Results, path: str | Path) -> dict[Path, dict]:
    """Write ``<stem>.summary/.stations/.pareto/.queues.parquet`` next to ``path``, each carrying the
    run metadata in the Parquet schema. Returns {file: metadata}."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = metadata(res)
    written = {}
    for part in ("summary", "stations", "pareto", "queues"):
        table = pa.Table.from_pandas(getattr(res, part), preserve_index=False)
        merged = {
            **(table.schema.metadata or {}),
            **{k.encode(): v.encode() for k, v in meta.items()},
        }
        f = path.with_name(f"{path.stem}.{part}.parquet")
        pq.write_table(table.replace_schema_metadata(merged), f)
        written[f] = meta
    return written


def read_metadata(file: str | Path) -> dict[str, str]:
    raw = pq.read_schema(file).metadata or {}
    return {k.decode(): v.decode() for k, v in raw.items() if k.startswith(b"ffdt.")}

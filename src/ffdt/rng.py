"""Random streams for common random numbers (CRN).

Each (replication, stream name) pair gets its own ``numpy.random.Generator`` derived from one
root seed through ``SeedSequence``. Stream identity depends on the *name*, not on creation order,
so adding or changing a station in a scenario leaves every other station's random numbers
unchanged. The global NumPy RNG is never used.
"""

from __future__ import annotations

import zlib

import numpy as np


def _name_key(name: str) -> int:
    return zlib.crc32(name.encode("utf-8"))  # stable across runs and Python versions


def stream(root_seed: int, replication: int, name: str) -> np.random.Generator:
    """Independent generator for one named purpose (e.g. ``"filler.failures"``) in one rep."""
    if root_seed < 0 or replication < 0:
        raise ValueError("root_seed and replication must be >= 0")
    ss = np.random.SeedSequence(entropy=root_seed, spawn_key=(replication, _name_key(name)))
    return np.random.Generator(np.random.PCG64(ss))

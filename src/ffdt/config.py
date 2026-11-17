"""Line configuration schema (T2.1.4).

Field names carry units: ``_min`` minutes, ``_vpm`` vials per minute, ``_vials`` vial counts,
``_frac`` fractions in [0, 1]. Every numeric value in a YAML config must carry a
``# src: B-xxx`` comment pointing at ``data/raw/benchmark_sources.csv``
(checked by ``tools/check_param_ids.py``).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

Pos = Annotated[float, Field(gt=0)]
NonNeg = Annotated[float, Field(ge=0)]
Frac = Annotated[float, Field(ge=0, le=1)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Triangular(_Strict):
    low_min: NonNeg
    mode_min: NonNeg
    high_min: Pos

    @model_validator(mode="after")
    def _order(self):
        if not (self.low_min <= self.mode_min <= self.high_min and self.low_min < self.high_min):
            raise ValueError("changeover needs low_min <= mode_min <= high_min and low < high")
        return self


class Failures(_Strict):
    mtbf_min: Pos  # operating time between breakdowns (A-002, A-035)
    mttr_mean_min: Pos
    mttr_cv: Pos


class MinorStops(_Strict):
    mean_between_min: Pos  # running time between minor stoppages (A-037)
    mean_duration_min: Pos


class Station(_Strict):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    kind: Literal["machine", "tunnel", "inspection"]
    rate_vpm: Pos
    residence_min: NonNeg = 0.0  # tunnel only
    failures: Failures | None = None
    minor_stops: MinorStops | None = None
    # Which changeovers this station performs (A-012):
    #   full      product-contact station: product_change / format_change / same_product
    #   packaging format_change if the format differs, else same_product (clearance, label swap)
    #   glass     format_change only (washer, tunnel handle empty glass)
    #   none      never changes over
    changeover_scope: Literal["full", "packaging", "glass", "none"] = "packaging"
    count: int = Field(default=1, ge=1, le=4)  # parallel identical units (SC-01 adds an AVI)

    @model_validator(mode="after")
    def _kind_rules(self):
        if self.kind == "tunnel" and self.residence_min <= 0:
            raise ValueError(f"tunnel {self.name!r} needs residence_min > 0")
        if self.kind != "tunnel" and self.residence_min:
            raise ValueError(f"residence_min is only valid for tunnels ({self.name!r})")
        return self


class Changeovers(_Strict):
    same_product: Triangular
    format_change: Triangular
    product_change: Triangular
    scale: Pos = 1.0  # scenario lever: 0.5 = changeover -50% (A-038)


class Batch(_Strict):
    product: str
    format: str
    size_vials: Annotated[int, Field(gt=0)]


class Staffing(_Strict):
    operator: Annotated[int, Field(ge=0)]
    mechanic: Annotated[int, Field(ge=0)]
    inspector: Annotated[int, Field(ge=0)]


class Quality(_Strict):
    defect_frac: Frac  # true rejectable defects among filled vials
    avi_detect_frac: Frac
    avi_false_reject_frac: Frac
    manual_confirm_frac: Frac
    manual_rate_vpm_per_inspector: Pos
    fill_weight_reject_frac: Frac


class QA(_Strict):
    reviewers: Annotated[int, Field(ge=1)]
    review_min_min: NonNeg
    review_mean_min: Pos
    review_cv: Pos
    release_hold_min: NonNeg = 0.0

    @model_validator(mode="after")
    def _mean_above_min(self):
        if self.review_mean_min <= self.review_min_min:
            raise ValueError("review_mean_min must exceed review_min_min")
        return self


class Calendar(_Strict):
    days: Annotated[int, Field(ge=1, le=7)]
    shifts_per_day: Annotated[int, Field(ge=1, le=3)]
    shift_min: Pos
    break_min_per_shift: NonNeg

    @model_validator(mode="after")
    def _break_fits(self):
        if self.break_min_per_shift >= self.shift_min:
            raise ValueError("break_min_per_shift must be shorter than shift_min")
        return self


class LineConfig(_Strict):
    name: str
    version: str
    sublot_vials: Annotated[int, Field(ge=1)]
    buffer_vials: Annotated[int, Field(ge=1)]
    calendar: Calendar
    stations: list[Station] = Field(min_length=1)
    products: list[str] = Field(min_length=1)
    formats: list[str] = Field(min_length=1)
    changeovers: Changeovers
    schedule: list[Batch] = Field(min_length=1)
    staffing: Staffing
    quality: Quality
    qa: QA

    @model_validator(mode="after")
    def _cross_checks(self):
        names = [s.name for s in self.stations]
        if len(names) != len(set(names)):
            raise ValueError(f"duplicate station names: {names}")
        if self.buffer_vials < 10 * self.sublot_vials:
            raise ValueError(
                f"buffer_vials ({self.buffer_vials}) must hold at least 10 sub-lots "
                f"({10 * self.sublot_vials} vials); see ADR-001"
            )
        if sum(s.kind == "inspection" for s in self.stations) != 1:
            raise ValueError("exactly one inspection (AVI) station is required")
        for i, b in enumerate(self.schedule):
            if b.product not in self.products:
                raise ValueError(f"schedule[{i}]: unknown product {b.product!r}")
            if b.format not in self.formats:
                raise ValueError(f"schedule[{i}]: unknown format {b.format!r}")
        return self

    @property
    def total_vials(self) -> int:
        return sum(b.size_vials for b in self.schedule)

    def station(self, name: str) -> Station:
        return next(s for s in self.stations if s.name == name)

    def hash(self) -> str:
        """Stable 12-hex-digit hash of the validated content (for result metadata and caching)."""
        blob = json.dumps(self.model_dump(mode="json"), sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()[:12]


def load_config(path: str | Path) -> LineConfig:
    with open(path, encoding="utf-8") as f:
        return LineConfig.model_validate(yaml.safe_load(f))


def apply_overrides(cfg: LineConfig, overrides: dict) -> LineConfig:
    """Deep-merge a dict of overrides (e.g. a scenario YAML) and re-validate."""

    def merge(a, b):
        if isinstance(a, dict) and isinstance(b, dict):
            out = dict(a)
            for k, v in b.items():
                out[k] = merge(a[k], v) if k in a else v
            return out
        return b  # lists and scalars are replaced wholesale

    overrides = dict(overrides)
    station_patch = overrides.pop("station_overrides", {})  # {station_name: {field: value}}
    data = merge(cfg.model_dump(), overrides)
    known = {s["name"] for s in data["stations"]}
    if unknown := set(station_patch) - known:
        raise ValueError(f"station_overrides for unknown stations: {sorted(unknown)}")
    data["stations"] = [merge(s, station_patch.get(s["name"], {})) for s in data["stations"]]
    return LineConfig.model_validate(data)

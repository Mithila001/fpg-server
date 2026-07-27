from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType

from pydantic import BaseModel, ConfigDict, StrictInt, ValidationError

from app.algorithms.types_new import (
    BuildableSpaceReferenceData,
    LandSide,
    RoadType,
    SetbackCalculationMode,
    SetbackProfile,
    UsableLandConstraints,
    ValidationLimits,
)

from .exceptions import ReferenceDataError

REFERENCE_DATA_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "buildable_space_reference_data.json"
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class _UnitsModel(_StrictModel):
    project_units_per_meter: StrictInt


class _SetbackProfileModel(_StrictModel):
    status: str
    description: str
    calculation_mode: SetbackCalculationMode
    base_setbacks: dict[LandSide, StrictInt]
    road_adjustments: dict[RoadType, dict[LandSide, StrictInt]]


class _UsableConstraintsModel(_StrictModel):
    minimum_width: StrictInt
    minimum_length: StrictInt
    search_resolution: StrictInt
    maximum_sweep_lines: StrictInt


class _ValidationLimitsModel(_StrictModel):
    minimum_vertex_count: StrictInt
    maximum_vertex_count: StrictInt
    maximum_absolute_coordinate: StrictInt


class _ReferenceDataModel(_StrictModel):
    schema_version: StrictInt
    units: _UnitsModel
    active_profile: str
    setback_profiles: dict[str, _SetbackProfileModel]
    usable_land_constraints: _UsableConstraintsModel
    validation_limits: _ValidationLimitsModel


def _require_exact_keys(
    label: str,
    actual: set[object],
    expected: set[object],
) -> None:
    if actual != expected:
        raise ReferenceDataError(f"{label} must define exactly {sorted(map(str, expected))}.")


@lru_cache(maxsize=None)
def _load_cached(path_text: str) -> BuildableSpaceReferenceData:
    path = Path(path_text)
    try:
        model = _ReferenceDataModel.model_validate_json(
            path.read_text(encoding="utf-8")
        )
    except (OSError, ValidationError, json.JSONDecodeError) as exc:
        raise ReferenceDataError(
            f"Could not load buildable-space reference data: {exc}"
        ) from exc

    if model.schema_version != 1:
        raise ReferenceDataError("Unsupported buildable-space schema_version.")
    if model.active_profile not in model.setback_profiles:
        raise ReferenceDataError("The active setback profile does not exist.")
    if model.units.project_units_per_meter <= 0:
        raise ReferenceDataError("project_units_per_meter must be positive.")

    profile_model = model.setback_profiles[model.active_profile]
    _require_exact_keys(
        "base_setbacks",
        set(profile_model.base_setbacks),
        set(LandSide),
    )
    _require_exact_keys(
        "road_adjustments",
        set(profile_model.road_adjustments),
        set(RoadType),
    )
    for road_type, adjustments in profile_model.road_adjustments.items():
        _require_exact_keys(
            f"road_adjustments.{road_type.value}",
            set(adjustments),
            set(LandSide),
        )
    values = tuple(profile_model.base_setbacks.values()) + tuple(
        value
        for adjustments in profile_model.road_adjustments.values()
        for value in adjustments.values()
    )
    if any(value < 0 for value in values):
        raise ReferenceDataError("Setback values must be non-negative integers.")

    usable = model.usable_land_constraints
    if any(
        value <= 0
        for value in (
            usable.minimum_width,
            usable.minimum_length,
            usable.search_resolution,
            usable.maximum_sweep_lines,
        )
    ):
        raise ReferenceDataError("Usable-land constraints must be positive.")
    limits = model.validation_limits
    if (
        limits.minimum_vertex_count < 4
        or limits.maximum_vertex_count < limits.minimum_vertex_count
        or limits.maximum_absolute_coordinate <= 0
    ):
        raise ReferenceDataError("Validation limits are inconsistent.")

    base = MappingProxyType(dict(profile_model.base_setbacks))
    road_adjustments = MappingProxyType(
        {
            road_type: MappingProxyType(dict(adjustments))
            for road_type, adjustments in profile_model.road_adjustments.items()
        }
    )
    return BuildableSpaceReferenceData(
        schema_version=model.schema_version,
        project_units_per_meter=model.units.project_units_per_meter,
        active_profile=SetbackProfile(
            name=model.active_profile,
            status=profile_model.status,
            description=profile_model.description,
            calculation_mode=profile_model.calculation_mode,
            base_setbacks=base,
            road_adjustments=road_adjustments,
        ),
        usable_land_constraints=UsableLandConstraints(
            minimum_width=usable.minimum_width,
            minimum_length=usable.minimum_length,
            search_resolution=usable.search_resolution,
            maximum_sweep_lines=usable.maximum_sweep_lines,
        ),
        validation_limits=ValidationLimits(
            minimum_vertex_count=limits.minimum_vertex_count,
            maximum_vertex_count=limits.maximum_vertex_count,
            maximum_absolute_coordinate=limits.maximum_absolute_coordinate,
        ),
    )


def load_buildable_space_reference_data(
    path: Path = REFERENCE_DATA_PATH,
) -> BuildableSpaceReferenceData:
    return _load_cached(str(path.resolve()))


def clear_buildable_space_reference_data_cache() -> None:
    _load_cached.cache_clear()

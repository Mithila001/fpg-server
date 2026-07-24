from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any


def _validate_boolean_fields(instance: Any) -> None:
    for item in fields(instance):
        value = getattr(instance, item.name)
        if not isinstance(value, bool):
            raise TypeError(f"{item.name} must be boolean")


@dataclass(frozen=True, slots=True)
class CandidateScoringVisualizationConfig:
    exterior_clearance: bool = True
    relationship_quality: bool = True
    spatial_distribution: bool = True
    zone_suitability: bool = True

    def __post_init__(self) -> None:
        _validate_boolean_fields(self)


@dataclass(frozen=True, slots=True)
class FloorPlanScoringVisualizationConfig:
    enclosed_voids: bool = True
    inward_recess: bool = True

    def __post_init__(self) -> None:
        _validate_boolean_fields(self)


@dataclass(frozen=True, slots=True)
class ScoringVisualizationConfig:
    enabled: bool = True
    candidate: CandidateScoringVisualizationConfig = field(
        default_factory=CandidateScoringVisualizationConfig
    )
    floor_plan: FloorPlanScoringVisualizationConfig = field(
        default_factory=FloorPlanScoringVisualizationConfig
    )

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be boolean")
        if not isinstance(self.candidate, CandidateScoringVisualizationConfig):
            raise TypeError(
                "candidate must be a CandidateScoringVisualizationConfig"
            )
        if not isinstance(self.floor_plan, FloorPlanScoringVisualizationConfig):
            raise TypeError(
                "floor_plan must be a FloorPlanScoringVisualizationConfig"
            )


DEFAULT_SCORING_VISUALIZATION_CONFIG = ScoringVisualizationConfig()

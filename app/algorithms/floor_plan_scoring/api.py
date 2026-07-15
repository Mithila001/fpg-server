from __future__ import annotations

from .config import ScoringProfile
from .defaults import DEFAULT_SCORING_PROFILE, create_default_registry
from .domain import FloorPlan, FloorPlanGenerationSpec
from .manager import FloorPlanScoreManager
from .registry import EvaluatorRegistry
from .types import FloorPlanScoringResult


def score_floor_plan(
    floor_plan: FloorPlan,
    specification: FloorPlanGenerationSpec,
    profile: ScoringProfile = DEFAULT_SCORING_PROFILE,
    *,
    registry: EvaluatorRegistry | None = None,
) -> FloorPlanScoringResult:
    """Score one completed floor plan without invoking application orchestration."""

    manager = FloorPlanScoreManager(
        registry=registry or create_default_registry(),
        profile=profile,
    )
    return manager.score(floor_plan, specification)

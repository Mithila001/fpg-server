# app/algorithms/floor_plan_scoring/api.py
from __future__ import annotations

from app.core.execution import ExecutionContext

from .config import ScoringProfile
from .defaults import DEFAULT_SCORING_PROFILE, create_default_registry
from .domain import FloorPlan, FloorPlanGenerationSpec
from .manager import FloorPlanScoreManager
from .logging import FloorPlanScoringEvent, log_floor_plan_scoring_event
from .registry import EvaluatorRegistry
from .types import FloorPlanScoringResult


def score_floor_plan(
    floor_plan: FloorPlan,
    specification: FloorPlanGenerationSpec,
    profile: ScoringProfile = DEFAULT_SCORING_PROFILE,
    *,
    registry: EvaluatorRegistry | None = None,
    execution_context: ExecutionContext | None = None,
) -> FloorPlanScoringResult:
    """Score one completed floor plan without invoking application orchestration."""

    log_floor_plan_scoring_event(
        execution_context,
        FloorPlanScoringEvent.STARTED,
        payload={
            "configured_group_count": len(profile.groups),
            "room_count": len(floor_plan.rooms),
        },
    )
    try:
        manager = FloorPlanScoreManager(
            registry=registry or create_default_registry(),
            profile=profile,
        )
        result = manager.score(floor_plan, specification)
    except Exception as exc:
        log_floor_plan_scoring_event(
            execution_context,
            FloorPlanScoringEvent.FAILED,
            level="ERROR",
            exception=exc,
        )
        raise
    log_floor_plan_scoring_event(
        execution_context,
        FloorPlanScoringEvent.COMPLETED,
        payload={
            "total_score": result.total_score,
            "passed_critical": result.passed_critical,
            "evaluator_count": len(result.evaluator_results),
        },
    )
    return result

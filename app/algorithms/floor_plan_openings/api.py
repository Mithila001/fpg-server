from __future__ import annotations

from .analysis import analyze_floor_plan
from .contracts import (
    OpeningDiagnostics,
    OpeningGenerationRequest,
    OpeningGenerationResult,
    OpeningGenerationStatus,
    OpeningIssue,
)
from .exceptions import OpeningInputError
from .logging import FloorPlanOpeningsEvent, log_openings_event
from .model import build_opening_model
from .registry import OpeningFeatureRegistry, create_default_registry
from .runner import solve_opening_model
from .validation import validate_request_floor_plan


def generate_openings(
    request: OpeningGenerationRequest,
    *,
    registry: OpeningFeatureRegistry | None = None,
) -> OpeningGenerationResult:
    """Generate openings on a finalized floor plan without mutating it."""

    context = request.execution_context
    log_openings_event(
        context,
        FloorPlanOpeningsEvent.STARTED,
        payload={
            "profile": request.profile.name,
            "room_count": len(request.floor_plan.rooms),
        },
    )
    try:
        validate_request_floor_plan(request.floor_plan, request.profile)
        prepared = analyze_floor_plan(request.floor_plan, request.profile)
    except OpeningInputError as exc:
        result = OpeningGenerationResult(
            status=OpeningGenerationStatus.INVALID_INPUT,
            floor_plan=None,
            profile_name=request.profile.name,
            message=str(exc),
            diagnostics=OpeningDiagnostics(
                raw_status="INVALID_INPUT",
                issues=(OpeningIssue("invalid_input", str(exc)),),
            ),
        )
        log_openings_event(
            context,
            FloorPlanOpeningsEvent.FAILED,
            level="WARNING",
            payload={"status": result.status.value},
            exception=exc,
        )
        return result

    try:
        built = build_opening_model(
            prepared,
            request.profile,
            registry or create_default_registry(),
        )
        result = solve_opening_model(request.floor_plan, built, request.profile)
    except Exception as exc:
        log_openings_event(
            context,
            FloorPlanOpeningsEvent.FAILED,
            level="ERROR",
            exception=exc,
        )
        raise
    log_openings_event(
        context,
        FloorPlanOpeningsEvent.COMPLETED,
        level="INFO" if result.solved else "WARNING",
        payload={
            "status": result.status.value,
            "solved": result.solved,
            "opening_count": (
                len(result.floor_plan.openings)
                if result.floor_plan is not None
                else 0
            ),
            "issue_count": len(result.diagnostics.issues),
        },
    )
    return result

# app/algorithms/floor_plan_solver/api.py
from __future__ import annotations

from .builder import build_model
from .constraints.defaults import build_default_registry
from .constraints.registry import ConstraintRegistry
from .contracts import FloorPlanSolveRequest, FloorPlanSolveResult
from .logging import FloorPlanSolverEvent, log_solver_event
from .preparation import prepare_problem
from .runner import solve_built_model


class FloorPlanSolver:
    """Small application service that owns one generic CP-SAT pipeline."""

    def __init__(self, registry: ConstraintRegistry | None = None) -> None:
        self._registry = registry or build_default_registry()

    @property
    def registry(self) -> ConstraintRegistry:
        return self._registry

    def solve(self, request: FloorPlanSolveRequest) -> FloorPlanSolveResult:
        context = request.execution_context
        log_solver_event(
            context,
            FloorPlanSolverEvent.STARTED,
            payload={
                "profile": request.profile.name,
                "candidate_hint_count": len(request.candidate_hints),
                "is_refinement": request.existing_floor_plan is not None,
            },
        )
        try:
            self._registry.validate_profile(request.profile)
            problem = prepare_problem(request)
            built = build_model(problem, request.profile, self._registry)
            result = solve_built_model(built, request.profile)
        except Exception as exc:
            log_solver_event(
                context,
                FloorPlanSolverEvent.FAILED,
                level="ERROR",
                exception=exc,
            )
            raise
        log_solver_event(
            context,
            FloorPlanSolverEvent.COMPLETED,
            level="INFO" if result.solved else "WARNING",
            payload={
                "profile": result.profile_name,
                "status": result.status.value,
                "solved": result.solved,
                "wall_time_seconds": result.diagnostics.wall_time_seconds,
                "objective_value": result.diagnostics.objective_value,
                "conflicts": result.diagnostics.conflicts,
                "branches": result.diagnostics.branches,
            },
        )
        return result


def generate_floor_plan(
    request: FloorPlanSolveRequest,
    *,
    registry: ConstraintRegistry | None = None,
) -> FloorPlanSolveResult:
    return FloorPlanSolver(registry=registry).solve(request)

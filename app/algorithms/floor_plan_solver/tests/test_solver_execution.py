from __future__ import annotations

from dataclasses import replace

from app.algorithms.floor_plan_solver import (
    FloorPlanSolveRequest,
    FloorPlanSolveResult,
    FloorPlanSolver,
    GenerationProfile,
    SolverStatus,
)
from app.algorithms.types_new.floor_plan_spec import FloorPlanGenerationSpec

from .assertions import (
    assert_back_exposure,
    assert_front_rules,
    assert_hallway_connectivity,
    assert_hard_room_relations,
    assert_minimum_coverage,
    assert_solved_result,
)
from .builders import build_infeasible_generation_spec


def test_real_solver_enforces_core_profile_constraints(
    initial_result: FloorPlanSolveResult,
    initial_profile: GenerationProfile,
    realistic_specification: FloorPlanGenerationSpec,
) -> None:
    floor_plan = assert_solved_result(initial_result, initial_profile.name)

    assert_hard_room_relations(
        floor_plan,
        realistic_specification,
        minimum_overlap=0.6,
    )
    assert_hallway_connectivity(floor_plan)
    assert_front_rules(floor_plan)
    assert_back_exposure(floor_plan)
    assert_minimum_coverage(
        floor_plan,
        realistic_specification,
        minimum_ratio=0.55,
    )


def test_solver_diagnostics_report_applied_profile_components(
    initial_result: FloorPlanSolveResult,
    initial_profile: GenerationProfile,
) -> None:
    diagnostics = initial_result.diagnostics
    assert diagnostics.applied_hard_constraints == tuple(
        use.key for use in initial_profile.hard_constraints
    )
    assert diagnostics.applied_soft_constraints == tuple(
        use.key for use in initial_profile.soft_constraints
    )
    assert diagnostics.penalty_terms
    assert diagnostics.objective_value is not None
    assert diagnostics.best_objective_bound is not None


def test_real_solver_reports_infeasible_model_without_fallback_plan(
    solver: FloorPlanSolver,
    initial_profile: GenerationProfile,
) -> None:
    profile = replace(
        initial_profile,
        solver=replace(initial_profile.solver, max_time_seconds=2.0),
    )
    result = solver.solve(
        FloorPlanSolveRequest(
            specification=build_infeasible_generation_spec(),
            profile=profile,
        )
    )

    assert result.status is SolverStatus.INFEASIBLE
    assert not result.solved
    assert result.floor_plan is None
    assert result.diagnostics.objective_value is None

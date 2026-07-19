from __future__ import annotations

import pytest

from app.algorithms.floor_plan_solver import (
    FloorPlanSolveResult,
    FloorPlanSolver,
    GenerationProfile,
    INITIAL_GENERATION_PROFILE,
    REFINEMENT_A_PROFILE,
    REFINEMENT_B_PROFILE,
)
from app.algorithms.floor_plan_solver.exceptions import MissingSeedError
from app.algorithms.types_new.floor_plan_spec import FloorPlanGenerationSpec

from .assertions import (
    assert_floor_plan_contract,
    assert_refinement_stays_within_seed_policy,
    assert_solved_result,
)
from .builders import build_solver_request
from .support import RefinementPipelineResults


def test_initial_generation_profile_runs_as_independent_first_stage(
    initial_result: FloorPlanSolveResult,
    initial_profile: GenerationProfile,
    realistic_specification: FloorPlanGenerationSpec,
) -> None:
    floor_plan = assert_solved_result(initial_result, "initial_generation")
    assert initial_profile.name == INITIAL_GENERATION_PROFILE.name
    assert "seed_stability" not in initial_result.diagnostics.applied_soft_constraints
    assert_floor_plan_contract(floor_plan, realistic_specification)


def test_initial_and_refinement_profiles_run_in_continuous_flow(
    refinement_pipeline: RefinementPipelineResults,
    refinement_a_profile: GenerationProfile,
    refinement_b_profile: GenerationProfile,
    realistic_specification: FloorPlanGenerationSpec,
) -> None:
    initial_plan = assert_solved_result(
        refinement_pipeline.initial,
        "initial_generation",
    )
    refinement_a_plan = assert_solved_result(
        refinement_pipeline.refinement_a,
        "refinement_a",
    )
    refinement_b_plan = assert_solved_result(
        refinement_pipeline.refinement_b,
        "refinement_b",
    )

    assert refinement_a_profile.name == REFINEMENT_A_PROFILE.name
    assert refinement_b_profile.name == REFINEMENT_B_PROFILE.name
    assert "seed_stability" in (
        refinement_pipeline.refinement_a.diagnostics.applied_soft_constraints
    )
    assert "seed_stability" in (
        refinement_pipeline.refinement_b.diagnostics.applied_soft_constraints
    )

    assert_floor_plan_contract(refinement_a_plan, realistic_specification)
    assert_floor_plan_contract(refinement_b_plan, realistic_specification)
    assert_refinement_stays_within_seed_policy(
        initial_plan,
        refinement_a_plan,
        refinement_a_profile,
    )
    assert_refinement_stays_within_seed_policy(
        refinement_a_plan,
        refinement_b_plan,
        refinement_b_profile,
    )


def test_refinement_profile_rejects_missing_existing_floor_plan(
    solver: FloorPlanSolver,
    refinement_a_profile: GenerationProfile,
    realistic_specification: FloorPlanGenerationSpec,
) -> None:
    request = build_solver_request(
        specification=realistic_specification,
        profile=refinement_a_profile,
        candidate_hints=(),
        existing_floor_plan=None,
    )

    with pytest.raises(MissingSeedError):
        solver.solve(request)

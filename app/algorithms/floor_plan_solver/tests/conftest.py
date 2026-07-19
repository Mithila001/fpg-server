from __future__ import annotations

import pytest

from app.algorithms.floor_plan_solver import (
    FloorPlanSolveResult,
    FloorPlanSolver,
    GenerationProfile,
)
from app.algorithms.floor_plan_solver.contracts import FloorPlanSolveRequest
from app.algorithms.types_new.floor_plan_spec import FloorPlanGenerationSpec

from .builders import (
    build_initial_integration_profile,
    build_realistic_candidate_hints,
    build_realistic_generation_spec,
    build_refinement_a_integration_profile,
    build_refinement_b_integration_profile,
    build_solver_request,
)
from .support import RefinementPipelineResults


@pytest.fixture(scope="session")
def solver() -> FloorPlanSolver:
    return FloorPlanSolver()


@pytest.fixture(scope="session")
def realistic_specification() -> FloorPlanGenerationSpec:
    return build_realistic_generation_spec()


@pytest.fixture(scope="session")
def initial_profile() -> GenerationProfile:
    return build_initial_integration_profile()


@pytest.fixture(scope="session")
def refinement_a_profile() -> GenerationProfile:
    return build_refinement_a_integration_profile()


@pytest.fixture(scope="session")
def refinement_b_profile() -> GenerationProfile:
    return build_refinement_b_integration_profile()


@pytest.fixture(scope="session")
def initial_request(
    realistic_specification: FloorPlanGenerationSpec,
    initial_profile: GenerationProfile,
) -> FloorPlanSolveRequest:
    return build_solver_request(
        specification=realistic_specification,
        profile=initial_profile,
        candidate_hints=build_realistic_candidate_hints(),
    )


@pytest.fixture(scope="session")
def initial_result(
    solver: FloorPlanSolver,
    initial_request: FloorPlanSolveRequest,
) -> FloorPlanSolveResult:
    return solver.solve(initial_request)


@pytest.fixture(scope="session")
def refinement_pipeline(
    solver: FloorPlanSolver,
    realistic_specification: FloorPlanGenerationSpec,
    initial_result: FloorPlanSolveResult,
    refinement_a_profile: GenerationProfile,
    refinement_b_profile: GenerationProfile,
) -> RefinementPipelineResults:
    if initial_result.floor_plan is None:
        pytest.fail(
            "Initial generation did not return a floor plan, so the real "
            "refinement pipeline cannot be executed"
        )

    refinement_a = solver.solve(
        build_solver_request(
            specification=realistic_specification,
            profile=refinement_a_profile,
            candidate_hints=(),
            existing_floor_plan=initial_result.floor_plan,
        )
    )
    if refinement_a.floor_plan is None:
        pytest.fail(
            "Refinement A did not return a floor plan, so Refinement B cannot run"
        )

    refinement_b = solver.solve(
        build_solver_request(
            specification=realistic_specification,
            profile=refinement_b_profile,
            candidate_hints=(),
            existing_floor_plan=refinement_a.floor_plan,
        )
    )
    return RefinementPipelineResults(
        initial=initial_result,
        refinement_a=refinement_a,
        refinement_b=refinement_b,
    )

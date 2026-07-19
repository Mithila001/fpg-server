from __future__ import annotations

from app.algorithms.floor_plan_solver import FloorPlanSolveResult, GenerationProfile
from app.algorithms.types_new.floor_plan_spec import FloorPlanGenerationSpec

from .assertions import (
    assert_floor_plan_contract,
    assert_room_size_contract,
    assert_rooms_do_not_overlap,
    assert_solved_result,
)


def test_valid_realistic_input_returns_floor_plan_contract(
    initial_result: FloorPlanSolveResult,
    initial_profile: GenerationProfile,
    realistic_specification: FloorPlanGenerationSpec,
) -> None:
    floor_plan = assert_solved_result(initial_result, initial_profile.name)
    assert_floor_plan_contract(floor_plan, realistic_specification)
    assert_room_size_contract(floor_plan, realistic_specification)
    assert_rooms_do_not_overlap(floor_plan)

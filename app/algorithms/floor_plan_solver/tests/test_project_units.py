from __future__ import annotations

from app.algorithms.floor_plan_solver import (
    FloorPlanSolveResult,
    INITIAL_GENERATION_PROFILE,
    REFINEMENT_A_PROFILE,
    REFINEMENT_B_PROFILE,
)
from app.algorithms.types_new.floor_plan_spec import FloorPlanGenerationSpec

from .assertions import assert_solved_result, assert_whole_project_unit_grid
from .builders import UNITS_PER_METER, load_scenario_data


def test_realistic_input_uses_ten_whole_units_per_meter(
    realistic_specification: FloorPlanGenerationSpec,
) -> None:
    data = load_scenario_data()
    assert data["measurement"]["units_per_meter"] == UNITS_PER_METER
    assert realistic_specification.floor.width == 12 * UNITS_PER_METER
    assert realistic_specification.floor.height == 11 * UNITS_PER_METER

    length_values = [
        realistic_specification.floor.width,
        realistic_specification.floor.height,
    ]
    for room in realistic_specification.rooms:
        length_values.extend(
            (
                room.size.min_width,
                room.size.max_width,
                room.size.min_height,
                room.size.max_height,
            )
        )
    assert all(float(value).is_integer() for value in length_values)


def test_builtin_profiles_do_not_subdivide_project_units() -> None:
    """One project unit is already the minimum supported 10 cm resolution."""

    for profile in (
        INITIAL_GENERATION_PROFILE,
        REFINEMENT_A_PROFILE,
        REFINEMENT_B_PROFILE,
    ):
        assert profile.preparation.coordinate_scale == 1, (
            f"Profile '{profile.name}' uses coordinate_scale="
            f"{profile.preparation.coordinate_scale}. With 10 units = 1 meter, "
            "the solver scale must be 1 to prevent sub-10 cm coordinates."
        )


def test_solver_output_stays_on_whole_project_unit_grid(
    initial_result: FloorPlanSolveResult,
) -> None:
    floor_plan = assert_solved_result(initial_result, "initial_generation")
    assert_whole_project_unit_grid(floor_plan)

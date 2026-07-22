"""Run the real Floor Plan Solver feature in a realistic mock environment.

This is an isolated algorithm feature check. It intentionally does not import
anything from ``test/flow-test`` or from another feature's test folder.
Only public production APIs from ``app/...`` are used.

Flow:

    realistic FloorPlanGenerationSpec
        -> initial generation with candidate hints
        -> Refinement A using the initial floor plan
        -> Refinement B using the Refinement A floor plan
        -> runtime validation
        -> JSON debug output for every stage

Run from the repository root:

    python test/algorithms/floor_plan_solver/run_floor_plan_solver.py
"""

from __future__ import annotations

import json
import math
from dataclasses import fields, is_dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from app.algorithms.floor_plan_solver import (
    INITIAL_GENERATION_PROFILE,
    REFINEMENT_A_PROFILE,
    REFINEMENT_B_PROFILE,
    FloorPlanSolveRequest,
    FloorPlanSolveResult,
    GenerationProfile,
    RoomPlacementHint,
    generate_floor_plan,
)
from app.algorithms.types_new import (
    ConstraintStrength,
    FloorPlan,
    FloorPlanGenerationSpec,
    FloorSpec,
    MatchPolicy,
    Polygon,
    RoomId,
    RoomRelationSpec,
    RoomSizeSpec,
    RoomSpec,
    RoomType,
)
from app.visualization.api import render_floor_plan_solver
from app.visualization.features.floor_plan_solver.models import (
    FloorPlanSolverStatus,
    FloorPlanSolverVisualization,
)
from app.util.output_paths import create_artifact_path, create_run_directory

UNITS_PER_METER = 10
UNIT_SIZE_CENTIMETERS = 10
RANDOM_SEED = 42
INITIAL_MAX_TIME_SECONDS = 8.0
REFINEMENT_MAX_TIME_SECONDS = 5.0
EPSILON = 1e-7
def room(
    room_id: str,
    room_type: RoomType,
    name: str,
    *,
    min_width: int,
    max_width: int,
    min_length: int,
    max_length: int,
    min_area: int,
    max_area: int,
    required: bool = True,
) -> RoomSpec:
    """Create one room specification using whole project units."""

    return RoomSpec(
        id=RoomId(room_id),
        room_type=room_type,
        name=name,
        size=RoomSizeSpec(
            min_width=min_width,
            max_width=max_width,
            min_length=min_length,
            max_length=max_length,
            min_area=min_area,
            max_area=max_area,
        ),
        required=required,
    )


def relation(
    source_room_id: str,
    target_room_ids: tuple[str, ...],
    *,
    match_policy: MatchPolicy,
    strength: ConstraintStrength,
) -> RoomRelationSpec:
    """Create one room relation for the mock specification."""

    return RoomRelationSpec(
        source_room_id=RoomId(source_room_id),
        target_room_ids=tuple(RoomId(room_id) for room_id in target_room_ids),
        match_policy=match_policy,
        strength=strength,
    )


def build_mock_specification() -> FloorPlanGenerationSpec:
    """Build a realistic single-story family-house specification.

    All dimensions are whole project units. Ten units equal one meter.
    """

    rooms = (
        room(
            "veranda",
            RoomType.VERANDA,
            "Front Veranda",
            min_width=50,
            max_width=75,
            min_length=10,
            max_length=15,
            min_area=500,
            max_area=1125,
        ),
        room(
            "living",
            RoomType.LIVING_ROOM,
            "Living Room",
            min_width=45,
            max_width=60,
            min_length=35,
            max_length=45,
            min_area=1575,
            max_area=2700,
        ),
        room(
            "dining",
            RoomType.DINING_ROOM,
            "Dining Room",
            min_width=30,
            max_width=40,
            min_length=25,
            max_length=35,
            min_area=750,
            max_area=1400,
        ),
        room(
            "kitchen",
            RoomType.KITCHEN,
            "Kitchen",
            min_width=30,
            max_width=40,
            min_length=25,
            max_length=35,
            min_area=750,
            max_area=1400,
        ),
        room(
            "hallway",
            RoomType.HALLWAY,
            "Main Hallway",
            min_width=10,
            max_width=16,
            min_length=40,
            max_length=58,
            min_area=400,
            max_area=928,
        ),
        room(
            "bedroom_1",
            RoomType.BEDROOM,
            "Bedroom 1",
            min_width=35,
            max_width=50,
            min_length=30,
            max_length=48,
            min_area=1050,
            max_area=2400,
        ),
        room(
            "bedroom_2",
            RoomType.BEDROOM,
            "Bedroom 2",
            min_width=35,
            max_width=48,
            min_length=30,
            max_length=40,
            min_area=1050,
            max_area=1920,
        ),
        room(
            "bathroom",
            RoomType.BATHROOM,
            "Common Bathroom",
            min_width=18,
            max_width=25,
            min_length=18,
            max_length=28,
            min_area=324,
            max_area=700,
        ),
        room(
            "attached_bathroom",
            RoomType.ATTACHED_BATHROOM,
            "Attached Bathroom",
            min_width=18,
            max_width=25,
            min_length=18,
            max_length=25,
            min_area=324,
            max_area=625,
        ),
    )

    room_relations = (
        relation(
            "veranda",
            ("living",),
            match_policy=MatchPolicy.AND,
            strength=ConstraintStrength.HARD,
        ),
        relation(
            "living",
            ("dining",),
            match_policy=MatchPolicy.AND,
            strength=ConstraintStrength.HARD,
        ),
        relation(
            "dining",
            ("kitchen",),
            match_policy=MatchPolicy.AND,
            strength=ConstraintStrength.HARD,
        ),
        relation(
            "bedroom_2",
            ("attached_bathroom",),
            match_policy=MatchPolicy.AND,
            strength=ConstraintStrength.HARD,
        ),
        relation(
            "bedroom_1",
            ("bathroom",),
            match_policy=MatchPolicy.OR,
            strength=ConstraintStrength.SOFT,
        ),
    )

    return FloorPlanGenerationSpec(
        floor=FloorSpec(width=120, length=110),
        rooms=rooms,
        room_relations=room_relations,
    )


def hint(
    room_id: str,
    x: int,
    y: int,
    width: int,
    length: int,
) -> RoomPlacementHint:
    """Create one realistic candidate-search placement hint."""

    return RoomPlacementHint(
        room_id=RoomId(room_id),
        x=x,
        y=y,
        width=width,
        length=length,
    )


def build_mock_candidate_hints() -> tuple[RoomPlacementHint, ...]:
    """Build candidate hints that approximate a plausible starting layout."""

    return (
        hint("veranda", 25, 0, 70, 12),
        hint("living", 20, 12, 55, 40),
        hint("dining", 75, 12, 35, 30),
        hint("kitchen", 75, 42, 35, 30),
        hint("hallway", 50, 52, 15, 58),
        hint("bedroom_1", 0, 52, 50, 48),
        hint("attached_bathroom", 65, 52, 25, 20),
        hint("bathroom", 90, 52, 20, 20),
        hint("bedroom_2", 65, 72, 45, 33),
    )


def build_runtime_profile(
    profile: GenerationProfile,
    *,
    max_time_seconds: float,
) -> GenerationProfile:
    """Keep production profile behavior while making the check deterministic."""

    return replace(
        profile,
        solver=replace(
            profile.solver,
            max_time_seconds=max_time_seconds,
            num_search_workers=1,
            random_seed=RANDOM_SEED,
            log_search_progress=False,
        ),
    )


def rectangle_bounds(polygon: Polygon) -> tuple[float, float, float, float]:
    """Return axis-aligned bounds and verify the solver returned a rectangle."""

    points = tuple(polygon.points)
    assert len(points) == 4, "Solver polygons must contain exactly four points."

    xs = {float(point.x) for point in points}
    ys = {float(point.y) for point in points}
    assert len(xs) == 2, "Solver polygon must have exactly two x coordinates."
    assert len(ys) == 2, "Solver polygon must have exactly two y coordinates."

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    assert max_x > min_x and max_y > min_y, "Solver rectangle cannot be empty."

    expected_corners = {
        (min_x, min_y),
        (max_x, min_y),
        (max_x, max_y),
        (min_x, max_y),
    }
    actual_corners = {(float(point.x), float(point.y)) for point in points}
    assert actual_corners == expected_corners, "Solver polygon must be axis-aligned."

    return min_x, min_y, max_x, max_y


def assert_whole_project_units(floor_plan: FloorPlan) -> None:
    """Verify all geometry respects the project's 10 cm whole-unit grid."""

    polygons = [floor_plan.boundary]
    polygons.extend(room.boundary for room in floor_plan.rooms)

    for polygon in polygons:
        for point in polygon.points:
            assert math.isclose(point.x, round(point.x), abs_tol=EPSILON), (
                f"x={point.x} is below the supported 10 cm project-unit resolution."
            )
            assert math.isclose(point.y, round(point.y), abs_tol=EPSILON), (
                f"y={point.y} is below the supported 10 cm project-unit resolution."
            )


def assert_no_room_overlap(floor_plan: FloorPlan) -> None:
    """Verify room interiors do not overlap; shared walls are allowed."""

    room_bounds = [
        (str(room.id), rectangle_bounds(room.boundary)) for room in floor_plan.rooms
    ]

    for index, (first_id, first) in enumerate(room_bounds):
        for second_id, second in room_bounds[index + 1 :]:
            first_min_x, first_min_y, first_max_x, first_max_y = first
            second_min_x, second_min_y, second_max_x, second_max_y = second

            overlap_width = min(first_max_x, second_max_x) - max(
                first_min_x,
                second_min_x,
            )
            overlap_length = min(first_max_y, second_max_y) - max(
                first_min_y,
                second_min_y,
            )

            assert not (overlap_width > EPSILON and overlap_length > EPSILON), (
                f"Rooms '{first_id}' and '{second_id}' overlap."
            )


def validate_solved_result(
    result: FloorPlanSolveResult,
    specification: FloorPlanGenerationSpec,
    *,
    expected_profile_name: str,
) -> FloorPlan:
    """Validate the main production contract returned by one solver stage."""

    assert result.solved, (
        f"Profile '{expected_profile_name}' did not solve: "
        f"status={result.status.value}, message={result.message}"
    )
    assert result.floor_plan is not None
    assert result.profile_name == expected_profile_name
    assert result.diagnostics.raw_status
    assert result.diagnostics.wall_time_seconds >= 0
    assert result.diagnostics.conflicts >= 0
    assert result.diagnostics.branches >= 0

    floor_plan = result.floor_plan
    floor_min_x, floor_min_y, floor_max_x, floor_max_y = rectangle_bounds(
        floor_plan.boundary
    )

    assert math.isclose(floor_min_x, 0.0, abs_tol=EPSILON)
    assert math.isclose(floor_min_y, 0.0, abs_tol=EPSILON)
    assert math.isclose(
        floor_max_x,
        specification.floor.width,
        abs_tol=EPSILON,
    )
    assert math.isclose(
        floor_max_y,
        specification.floor.length,
        abs_tol=EPSILON,
    )

    expected_required_ids = {
        str(room_spec.id) for room_spec in specification.rooms if room_spec.required
    }
    actual_ids = [str(room.id) for room in floor_plan.rooms]

    assert len(actual_ids) == len(set(actual_ids)), "Returned room IDs must be unique."
    assert expected_required_ids.issubset(set(actual_ids)), (
        "The solver result is missing one or more required rooms."
    )

    for room_result in floor_plan.rooms:
        min_x, min_y, max_x, max_y = rectangle_bounds(room_result.boundary)
        assert min_x >= floor_min_x - EPSILON
        assert min_y >= floor_min_y - EPSILON
        assert max_x <= floor_max_x + EPSILON
        assert max_y <= floor_max_y + EPSILON

    assert_whole_project_units(floor_plan)
    assert_no_room_overlap(floor_plan)
    return floor_plan


def assert_refinement_respects_seed_policy(
    previous: FloorPlan,
    refined: FloorPlan,
    profile: GenerationProfile,
) -> None:
    """Verify a refinement stays inside the profile's movement tolerances."""

    previous_rooms = {str(room.id): room for room in previous.rooms}
    refined_rooms = {str(room.id): room for room in refined.rooms}
    assert set(previous_rooms) == set(refined_rooms), (
        "Refinement changed the set of generated rooms."
    )

    scale = profile.preparation.coordinate_scale

    def effective_tolerance(value: float | None) -> float | None:
        if value is None:
            return None
        return math.ceil(value * scale - 1e-9) / scale

    position_tolerance = effective_tolerance(profile.seed.position_tolerance)
    size_tolerance = effective_tolerance(profile.seed.size_tolerance)

    for room_id, previous_room in previous_rooms.items():
        old_min_x, old_min_y, old_max_x, old_max_y = rectangle_bounds(
            previous_room.boundary
        )
        new_min_x, new_min_y, new_max_x, new_max_y = rectangle_bounds(
            refined_rooms[room_id].boundary
        )

        old_width = old_max_x - old_min_x
        old_length = old_max_y - old_min_y
        new_width = new_max_x - new_min_x
        new_length = new_max_y - new_min_y

        if position_tolerance is not None:
            assert abs(new_min_x - old_min_x) <= position_tolerance + EPSILON
            assert abs(new_min_y - old_min_y) <= position_tolerance + EPSILON

        if size_tolerance is not None:
            assert abs(new_width - old_width) <= size_tolerance + EPSILON
            assert abs(new_length - old_length) <= size_tolerance + EPSILON


def jsonable(value: Any) -> Any:
    """Convert solver dataclasses and enums into JSON-compatible data."""

    if is_dataclass(value):
        return {
            field.name: jsonable(getattr(value, field.name)) for field in fields(value)
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def save_stage_output(
    output_directory: Path,
    descriptive_name: str,
    request: FloorPlanSolveRequest,
    result: FloorPlanSolveResult,
) -> Path:
    """Save one complete request/result pair for debugging."""

    output_path = create_artifact_path(
        output_directory, descriptive_name, "json"
    )
    payload = {
        "measurement": {
            "units_per_meter": UNITS_PER_METER,
            "unit_size_centimeters": UNIT_SIZE_CENTIMETERS,
            "dimensions_use_whole_project_units": True,
        },
        "request": jsonable(request),
        "result": jsonable(result),
    }
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return output_path


def print_stage_result(
    result: FloorPlanSolveResult,
    output_path: Path,
) -> None:
    """Print a useful human-readable summary for one solver stage."""

    print("\n" + "=" * 78)
    print(result.profile_name.upper())
    print("=" * 78)
    print(f"Status: {result.status.value}")
    print(f"Message: {result.message}")
    print(f"Raw OR-Tools status: {result.diagnostics.raw_status}")
    print(f"Wall time: {result.diagnostics.wall_time_seconds:.3f}s")
    print(f"Objective value: {result.diagnostics.objective_value}")
    print(f"Best objective bound: {result.diagnostics.best_objective_bound}")
    print(f"Conflicts: {result.diagnostics.conflicts}")
    print(f"Branches: {result.diagnostics.branches}")
    print("Hard constraints: " + ", ".join(result.diagnostics.applied_hard_constraints))
    print("Soft constraints: " + ", ".join(result.diagnostics.applied_soft_constraints))

    if result.floor_plan is not None:
        print(f"Rooms generated: {len(result.floor_plan.rooms)}")
        print("\nRoom geometry:")

        for room_result in result.floor_plan.rooms:
            min_x, min_y, max_x, max_y = rectangle_bounds(room_result.boundary)
            width = max_x - min_x
            length = max_y - min_y
            area = width * length
            print(
                f"  {str(room_result.id):22} "
                f"x={min_x:5.1f} y={min_y:5.1f} "
                f"w={width:5.1f} h={length:5.1f} "
                f"area={area:7.1f}"
            )

    print(f"\nJSON output: {output_path}")


def main() -> None:
    output_directory = create_run_directory(
        "json", "floor_plan_solver", "manual-floor-plan-solver"
    )
    specification = build_mock_specification()
    candidate_hints = build_mock_candidate_hints()

    initial_profile = build_runtime_profile(
        INITIAL_GENERATION_PROFILE,
        max_time_seconds=INITIAL_MAX_TIME_SECONDS,
    )
    refinement_a_profile = build_runtime_profile(
        REFINEMENT_A_PROFILE,
        max_time_seconds=REFINEMENT_MAX_TIME_SECONDS,
    )
    refinement_b_profile = build_runtime_profile(
        REFINEMENT_B_PROFILE,
        max_time_seconds=REFINEMENT_MAX_TIME_SECONDS,
    )

    print("Floor Plan Solver realistic algorithm run")
    print(
        f"Floor: {specification.floor.width} x {specification.floor.length} units "
        f"({specification.floor.width / UNITS_PER_METER:.1f} x "
        f"{specification.floor.length / UNITS_PER_METER:.1f} meters)"
    )
    print(f"Rooms: {len(specification.rooms)}")
    print(f"Candidate hints: {len(candidate_hints)}")
    print(f"Project measurement: {UNITS_PER_METER} units = 1 meter")

    initial_request = FloorPlanSolveRequest(
        specification=specification,
        profile=initial_profile,
        candidate_hints=candidate_hints,
    )
    initial_result = generate_floor_plan(initial_request)
    initial_floor_plan = validate_solved_result(
        initial_result,
        specification,
        expected_profile_name=INITIAL_GENERATION_PROFILE.name,
    )
    render_floor_plan_solver(
        FloorPlanSolverVisualization(
            floor_plan=initial_floor_plan,
            profile_name=initial_result.profile_name,
            status=FloorPlanSolverStatus(initial_result.status),
        ),
        output_name="initial_generation",
    )
    assert "seed_stability" not in (initial_result.diagnostics.applied_soft_constraints)
    initial_output = save_stage_output(
        output_directory,
        "initial-generation",
        initial_request,
        initial_result,
    )
    print_stage_result(initial_result, initial_output)

    refinement_a_request = FloorPlanSolveRequest(
        specification=specification,
        profile=refinement_a_profile,
        existing_floor_plan=initial_floor_plan,
    )
    refinement_a_result = generate_floor_plan(refinement_a_request)

    refinement_a_floor_plan = validate_solved_result(
        refinement_a_result,
        specification,
        expected_profile_name=REFINEMENT_A_PROFILE.name,
    )
    render_floor_plan_solver(
        FloorPlanSolverVisualization(
            floor_plan=refinement_a_floor_plan,
            profile_name=refinement_a_result.profile_name,
            status=FloorPlanSolverStatus(refinement_a_result.status),
        ),
        output_name="refinement_a",
    )
    assert "seed_stability" in (
        refinement_a_result.diagnostics.applied_soft_constraints
    )
    assert_refinement_respects_seed_policy(
        initial_floor_plan,
        refinement_a_floor_plan,
        refinement_a_profile,
    )
    refinement_a_output = save_stage_output(
        output_directory,
        "refinement-a",
        refinement_a_request,
        refinement_a_result,
    )
    print_stage_result(refinement_a_result, refinement_a_output)

    refinement_b_request = FloorPlanSolveRequest(
        specification=specification,
        profile=refinement_b_profile,
        existing_floor_plan=refinement_a_floor_plan,
    )
    refinement_b_result = generate_floor_plan(refinement_b_request)
    refinement_b_floor_plan = validate_solved_result(
        refinement_b_result,
        specification,
        expected_profile_name=REFINEMENT_B_PROFILE.name,
    )
    render_floor_plan_solver(
        FloorPlanSolverVisualization(
            floor_plan=refinement_b_floor_plan,
            profile_name=refinement_b_result.profile_name,
            status=FloorPlanSolverStatus(refinement_b_result.status),
        ),
        output_name="refinement_b",
    )
    assert "seed_stability" in (
        refinement_b_result.diagnostics.applied_soft_constraints
    )
    assert_refinement_respects_seed_policy(
        refinement_a_floor_plan,
        refinement_b_floor_plan,
        refinement_b_profile,
    )
    refinement_b_output = save_stage_output(
        output_directory,
        "refinement-b",
        refinement_b_request,
        refinement_b_result,
    )
    print_stage_result(refinement_b_result, refinement_b_output)

    print("\n" + "#" * 78)
    print("FLOOR PLAN SOLVER ALGORITHM CHECK PASSED")
    print("#" * 78)
    print("Initial generation completed successfully.")
    print("Refinement A accepted the initial floor plan and completed successfully.")
    print("Refinement B accepted Refinement A output and completed successfully.")
    print("All generated geometry stayed inside the floor and on whole project units.")


if __name__ == "__main__":
    main()

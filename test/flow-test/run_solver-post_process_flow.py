"""Run Floor Plan Solver and Floor Plan Post Processing as one flow check.

This file is intentionally self-contained inside ``test/flow-test``. It does
not import builders, validators, serializers, or any other code from the
``test`` directory. Only public production APIs from ``app/...`` are used.

Flow:

    realistic FloorPlanGenerationSpec
        -> generate biased random candidate hints from the specification
        -> initial solver generation with those candidate hints
        -> Refinement A using the initial floor plan
        -> Refinement B using the Refinement A floor plan
        -> preserve named solver floor-plan stage snapshots
        -> post-process a deep copy of the Refinement B floor plan
        -> preserve the named post-processing floor-plan stage snapshot
        -> save one combined JSON debug output

The named stage arrays are retained and passed to the general floor-plan
visualizer after the JSON debug output is saved.

Run from the repository root:

    python test/flow-test/run_solver-post_process_flow.py
"""

from __future__ import annotations

import copy
import json
import math
import random
from dataclasses import fields, is_dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, TypedDict

from app.algorithms.floor_plan_post_processing import (
    INITIAL_GENERATION_PROFILE as POST_PROCESSING_INITIAL_GENERATION_PROFILE,
)
from app.algorithms.floor_plan_post_processing import (
    PipelineStatus,
    PostProcessingRequest,
    PostProcessingResult,
    ProcessorStatus,
    post_process_floor_plan,
)
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
    RoomRole,
    RoomSizeSpec,
    RoomSpec,
    RoomType,
)
from app.visualization.api import (
    FloorPlanFlowVisualization,
    FloorPlanVisualizationStage,
    render_floor_plan_general,
)

UNITS_PER_METER = 10
UNIT_SIZE_CENTIMETERS = 10
RANDOM_SEED = random.randrange(1_000_000)
INITIAL_MAX_TIME_SECONDS = 8.0
REFINEMENT_MAX_TIME_SECONDS = 5.0
EPSILON = 1e-7
OUTPUT_DIR = Path(__file__).resolve().parent / "output" / "solver_post_process"
OUTPUT_FILENAME = "solver_post_process_flow.json"
REQUEST_ID = "solver-post-process-flow"


class FloorPlanStage(TypedDict):
    """One named floor-plan snapshot prepared for future visualization."""

    stage: str
    feature: str
    profile: str
    status: str
    floor_plan: FloorPlan


def room(
    room_id: str,
    room_type: RoomType,
    name: str,
    *,
    min_width: int,
    max_width: int,
    min_height: int,
    max_height: int,
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
            min_height=min_height,
            max_height=max_height,
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
            min_height=10,
            max_height=15,
            min_area=500,
            max_area=1125,
        ),
        room(
            "living",
            RoomType.LIVING_ROOM,
            "Living Room",
            min_width=45,
            max_width=60,
            min_height=35,
            max_height=45,
            min_area=1575,
            max_area=2700,
        ),
        room(
            "dining",
            RoomType.DINING_ROOM,
            "Dining Room",
            min_width=30,
            max_width=40,
            min_height=25,
            max_height=35,
            min_area=750,
            max_area=1400,
        ),
        room(
            "kitchen",
            RoomType.KITCHEN,
            "Kitchen",
            min_width=30,
            max_width=40,
            min_height=25,
            max_height=35,
            min_area=750,
            max_area=1400,
        ),
        room(
            "hallway",
            RoomType.HALLWAY,
            "Main Hallway",
            min_width=10,
            max_width=16,
            min_height=40,
            max_height=58,
            min_area=400,
            max_area=928,
        ),
        room(
            "bedroom_1",
            RoomType.BEDROOM,
            "Bedroom 1",
            min_width=35,
            max_width=50,
            min_height=30,
            max_height=48,
            min_area=1050,
            max_area=2400,
        ),
        room(
            "bedroom_2",
            RoomType.BEDROOM,
            "Bedroom 2",
            min_width=35,
            max_width=48,
            min_height=30,
            max_height=40,
            min_area=1050,
            max_area=1920,
        ),
        room(
            "bathroom",
            RoomType.BATHROOM,
            "Common Bathroom",
            min_width=18,
            max_width=25,
            min_height=18,
            max_height=28,
            min_area=324,
            max_area=700,
        ),
        room(
            "attached_bathroom",
            RoomType.ATTACHED_BATHROOM,
            "Attached Bathroom",
            min_width=18,
            max_width=25,
            min_height=18,
            max_height=25,
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
        floor=FloorSpec(width=120, height=110),
        rooms=rooms,
        room_relations=room_relations,
    )


def hint(
    room_id: str,
    x: int,
    y: int,
    width: int,
    height: int,
) -> RoomPlacementHint:
    """Create one whole-unit room placement hint."""

    return RoomPlacementHint(
        room_id=RoomId(room_id),
        x=x,
        y=y,
        width=width,
        height=height,
    )


def choose_random_room_dimensions(
    room_spec: RoomSpec,
    *,
    floor_width: int,
    floor_height: int,
    rng: random.Random,
) -> tuple[int, int]:
    """Choose dimensions that satisfy the room's declared size limits.

    Valid whole-unit width/height pairs are enumerated first. This prevents the
    random hint generator from producing a width and height whose combined area
    violates the room specification.
    """

    min_width = max(1, math.ceil(room_spec.size.min_width))
    max_width = min(floor_width, math.floor(room_spec.size.max_width))
    min_height = max(1, math.ceil(room_spec.size.min_height))
    max_height = min(floor_height, math.floor(room_spec.size.max_height))

    valid_dimensions = [
        (width, height)
        for width in range(min_width, max_width + 1)
        for height in range(min_height, max_height + 1)
        if room_spec.size.min_area <= width * height <= room_spec.size.max_area
    ]

    if not valid_dimensions:
        raise ValueError(
            f"Room '{room_spec.id}' has no whole-unit dimensions that satisfy "
            "its width, height, area, and floor-boundary limits."
        )

    return rng.choice(valid_dimensions)


def biased_coordinate(
    maximum: int,
    *,
    start_ratio: float,
    end_ratio: float,
    rng: random.Random,
) -> int:
    """Sample one coordinate from a normalized section of its valid range."""

    if maximum <= 0:
        return 0

    lower = max(0, min(maximum, round(maximum * start_ratio)))
    upper = max(lower, min(maximum, round(maximum * end_ratio)))
    return rng.randint(lower, upper)


def choose_biased_room_position(
    room_spec: RoomSpec,
    *,
    width: int,
    height: int,
    floor_width: int,
    floor_height: int,
    room_type_index: int,
    rng: random.Random,
) -> tuple[int, int]:
    """Choose a random position biased by the architectural room type.

    The biases are deliberately soft. They only produce a better starting
    suggestion; CP-SAT remains responsible for enforcing the real geometry and
    relationship constraints. The project treats y=0 as the front facade.
    """

    max_x = max(0, floor_width - width)
    max_y = max(0, floor_height - height)

    if room_spec.room_type is RoomType.VERANDA:
        return (
            biased_coordinate(max_x, start_ratio=0.15, end_ratio=0.85, rng=rng),
            0,
        )

    if room_spec.room_type is RoomType.LIVING_ROOM:
        return (
            biased_coordinate(max_x, start_ratio=0.10, end_ratio=0.45, rng=rng),
            biased_coordinate(max_y, start_ratio=0.00, end_ratio=0.25, rng=rng),
        )

    if room_spec.room_type is RoomType.DINING_ROOM:
        return (
            biased_coordinate(max_x, start_ratio=0.40, end_ratio=0.75, rng=rng),
            biased_coordinate(max_y, start_ratio=0.15, end_ratio=0.50, rng=rng),
        )

    if room_spec.room_type is RoomType.KITCHEN:
        return (
            biased_coordinate(max_x, start_ratio=0.55, end_ratio=1.00, rng=rng),
            biased_coordinate(max_y, start_ratio=0.40, end_ratio=0.80, rng=rng),
        )

    if room_spec.room_type is RoomType.HALLWAY:
        return (
            biased_coordinate(max_x, start_ratio=0.38, end_ratio=0.62, rng=rng),
            biased_coordinate(max_y, start_ratio=0.20, end_ratio=0.60, rng=rng),
        )

    if room_spec.room_type is RoomType.BEDROOM:
        # Alternate bedroom hints between the left and right rear sections.
        if room_type_index % 2 == 0:
            x_start, x_end = 0.00, 0.30
        else:
            x_start, x_end = 0.70, 1.00
        return (
            biased_coordinate(max_x, start_ratio=x_start, end_ratio=x_end, rng=rng),
            biased_coordinate(max_y, start_ratio=0.50, end_ratio=1.00, rng=rng),
        )

    if room_spec.room_type is RoomType.ATTACHED_BATHROOM:
        return (
            biased_coordinate(max_x, start_ratio=0.55, end_ratio=1.00, rng=rng),
            biased_coordinate(max_y, start_ratio=0.50, end_ratio=1.00, rng=rng),
        )

    if room_spec.room_type is RoomType.BATHROOM:
        return (
            biased_coordinate(max_x, start_ratio=0.35, end_ratio=0.85, rng=rng),
            biased_coordinate(max_y, start_ratio=0.45, end_ratio=0.90, rng=rng),
        )

    if room_spec.room_type is RoomType.GARAGE:
        return (
            biased_coordinate(max_x, start_ratio=0.00, end_ratio=0.25, rng=rng),
            biased_coordinate(max_y, start_ratio=0.00, end_ratio=0.20, rng=rng),
        )

    # OPEN_AREA and any future room type receive an unrestricted position.
    return rng.randint(0, max_x), rng.randint(0, max_y)


def build_biased_random_candidate_hints(
    specification: FloorPlanGenerationSpec,
    *,
    seed: int = RANDOM_SEED,
) -> tuple[RoomPlacementHint, ...]:
    """Generate repeatable random hints with lightweight room-type bias.

    The same seed and specification always produce the same hints, which keeps
    this flow check reproducible. Change the seed to explore another starting
    arrangement. Initial overlaps are allowed because hints are soft guidance.
    """

    floor_width = math.floor(specification.floor.width)
    floor_height = math.floor(specification.floor.height)
    if floor_width <= 0 or floor_height <= 0:
        raise ValueError("Floor dimensions must be positive whole project units.")

    rng = random.Random(seed)
    room_type_counts: dict[RoomType, int] = {}
    candidate_hints: list[RoomPlacementHint] = []

    for room_spec in specification.rooms:
        room_type_index = room_type_counts.get(room_spec.room_type, 0)
        room_type_counts[room_spec.room_type] = room_type_index + 1

        width, height = choose_random_room_dimensions(
            room_spec,
            floor_width=floor_width,
            floor_height=floor_height,
            rng=rng,
        )
        x, y = choose_biased_room_position(
            room_spec,
            width=width,
            height=height,
            floor_width=floor_width,
            floor_height=floor_height,
            room_type_index=room_type_index,
            rng=rng,
        )

        candidate_hints.append(
            hint(
                str(room_spec.id),
                x=x,
                y=y,
                width=width,
                height=height,
            )
        )

    return tuple(candidate_hints)


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
            overlap_height = min(first_max_y, second_max_y) - max(
                first_min_y,
                second_min_y,
            )

            assert not (overlap_width > EPSILON and overlap_height > EPSILON), (
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
        specification.floor.height,
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
        old_height = old_max_y - old_min_y
        new_width = new_max_x - new_min_x
        new_height = new_max_y - new_min_y

        if position_tolerance is not None:
            assert abs(new_min_x - old_min_x) <= position_tolerance + EPSILON
            assert abs(new_min_y - old_min_y) <= position_tolerance + EPSILON

        if size_tolerance is not None:
            assert abs(new_width - old_width) <= size_tolerance + EPSILON
            assert abs(new_height - old_height) <= size_tolerance + EPSILON


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
    if isinstance(value, (set, frozenset)):
        return [jsonable(item) for item in sorted(value, key=str)]
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def make_floor_plan_stage(
    *,
    stage: str,
    feature: str,
    profile: str,
    status: str,
    floor_plan: FloorPlan,
) -> FloorPlanStage:
    """Create an isolated named snapshot for future visualization consumers."""

    return {
        "stage": stage,
        "feature": feature,
        "profile": profile,
        "status": status,
        "floor_plan": copy.deepcopy(floor_plan),
    }


def validate_post_processing_result(
    result: PostProcessingResult,
    specification: FloorPlanGenerationSpec,
    *,
    expected_processor_count: int,
) -> FloorPlan:
    """Validate the feature boundary and final post-processed floor plan."""

    assert result.status is PipelineStatus.SUCCESS, (
        "Post processing failed: "
        f"failure={result.failure.code if result.failure else None}, "
        f"message={result.failure.message if result.failure else None}"
    )
    assert result.failure is None
    assert len(result.executions) == expected_processor_count, (
        "Post processing did not execute every processor in the selected profile."
    )

    unsuccessful = [
        execution
        for execution in result.executions
        if execution.status in {ProcessorStatus.FAILED, ProcessorStatus.SKIPPED}
    ]
    assert not unsuccessful, (
        "One or more post-processing processors failed or were skipped: "
        + ", ".join(
            f"{execution.processor_id}={execution.status.value}"
            for execution in unsuccessful
        )
    )

    floor_plan = result.floor_plan
    assert not floor_plan.openings, (
        "Post processing must run before opening generation for this profile."
    )
    assert all(
        room.role is not RoomRole.SOLVER_PLACEHOLDER for room in floor_plan.rooms
    ), "Post-processing output still contains solver placeholder rooms."

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
        specification.floor.height,
        abs_tol=EPSILON,
    )

    room_ids = [room.id for room in floor_plan.rooms]
    room_names = [room.name for room in floor_plan.rooms]
    assert len(room_ids) == len(set(room_ids)), (
        "Post-processed room IDs must be unique."
    )
    assert len(room_names) == len(set(room_names)), (
        "Post-processed room names must be unique."
    )

    room_id_set = set(room_ids)
    for room_result in floor_plan.rooms:
        assert len(room_result.boundary.points) >= 3, (
            f"Room '{room_result.id}' returned an invalid polygon."
        )
        for point in room_result.boundary.points:
            assert point.x >= floor_min_x - EPSILON
            assert point.y >= floor_min_y - EPSILON
            assert point.x <= floor_max_x + EPSILON
            assert point.y <= floor_max_y + EPSILON
        if room_result.parent_room_id is not None:
            assert room_result.parent_room_id in room_id_set

    for source_room_id, target_room_id in floor_plan.identity_redirects.items():
        assert source_room_id not in room_id_set
        assert target_room_id in room_id_set

    assert_whole_project_units(floor_plan)
    return floor_plan


def print_solver_stage_result(result: FloorPlanSolveResult) -> None:
    """Print a concise solver-stage summary."""

    print("\n" + "=" * 78)
    print(result.profile_name.upper())
    print("=" * 78)
    print(f"Status: {result.status.value}")
    print(f"Message: {result.message}")
    print(f"Raw OR-Tools status: {result.diagnostics.raw_status}")
    print(f"Wall time: {result.diagnostics.wall_time_seconds:.3f}s")
    print(f"Objective value: {result.diagnostics.objective_value}")
    print(f"Conflicts: {result.diagnostics.conflicts}")
    print(f"Branches: {result.diagnostics.branches}")
    if result.floor_plan is not None:
        print(f"Rooms generated: {len(result.floor_plan.rooms)}")


def print_post_processing_result(result: PostProcessingResult) -> None:
    """Print a concise processor-by-processor post-processing summary."""

    print("\n" + "=" * 78)
    print("POST PROCESSING")
    print("=" * 78)
    print(f"Status: {result.status.value}")
    print(f"Rooms returned: {len(result.floor_plan.rooms)}")
    print(
        "Applied transformations: "
        + (", ".join(sorted(result.floor_plan.applied_transformations)) or "none")
    )

    for execution in result.executions:
        rollback_note = " (rolled back)" if execution.rolled_back else ""
        print(
            f"  {execution.processor_id:30} "
            f"{execution.status.value:16} "
            f"{execution.duration_ms:9.3f} ms{rollback_note}"
        )


def save_flow_output(
    *,
    specification: FloorPlanGenerationSpec,
    candidate_hints: tuple[RoomPlacementHint, ...],
    solver_floor_plan_stages: list[FloorPlanStage],
    post_processing_floor_plan_stages: list[FloorPlanStage],
    initial_request: FloorPlanSolveRequest,
    initial_result: FloorPlanSolveResult,
    refinement_a_request: FloorPlanSolveRequest,
    refinement_a_result: FloorPlanSolveResult,
    refinement_b_request: FloorPlanSolveRequest,
    refinement_b_result: FloorPlanSolveResult,
    post_processing_input_snapshot: FloorPlan,
    post_processing_request: PostProcessingRequest,
    post_processing_result: PostProcessingResult,
) -> Path:
    """Save the complete flow and both named visualization-stage arrays."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / OUTPUT_FILENAME

    # The post-processing pipeline mutates request.floor_plan in place. Use the
    # preserved input snapshot here so the JSON accurately shows both sides of
    # the feature boundary.
    post_processing_request_payload = {
        "floor_plan": post_processing_input_snapshot,
        "profile": post_processing_request.profile,
        "specification": post_processing_request.specification,
        "request_id": post_processing_request.request_id,
    }

    payload = {
        "measurement": {
            "units_per_meter": UNITS_PER_METER,
            "unit_size_centimeters": UNIT_SIZE_CENTIMETERS,
            "dimensions_use_whole_project_units": True,
        },
        "specification": jsonable(specification),
        "candidate_hints": jsonable(candidate_hints),
        "visualization_inputs": {
            "solver_floor_plan_stages": jsonable(solver_floor_plan_stages),
            "post_processing_floor_plan_stages": jsonable(
                post_processing_floor_plan_stages
            ),
        },
        "solver": {
            "initial_generation": {
                "request": jsonable(initial_request),
                "result": jsonable(initial_result),
            },
            "refinement_a": {
                "request": jsonable(refinement_a_request),
                "result": jsonable(refinement_a_result),
            },
            "refinement_b": {
                "request": jsonable(refinement_b_request),
                "result": jsonable(refinement_b_result),
            },
        },
        "post_processing": {
            "request": jsonable(post_processing_request_payload),
            "result": jsonable(post_processing_result),
        },
    }

    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return output_path


def main() -> None:
    specification = build_mock_specification()
    candidate_hints = build_biased_random_candidate_hints(
        specification,
        seed=RANDOM_SEED,
    )

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

    # These are intentionally separate because the planned visualizers have
    # different responsibilities. Every stage stores an isolated FloorPlan
    # snapshot, so later in-place transformations cannot rewrite history.
    solver_floor_plan_stages: list[FloorPlanStage] = []
    post_processing_floor_plan_stages: list[FloorPlanStage] = []

    print("Solver -> Post Processing realistic flow run")
    print(
        f"Floor: {specification.floor.width} x {specification.floor.height} units "
        f"({specification.floor.width / UNITS_PER_METER:.1f} x "
        f"{specification.floor.height / UNITS_PER_METER:.1f} meters)"
    )
    print(f"Rooms requested: {len(specification.rooms)}")
    print(f"Candidate hints: {len(candidate_hints)}")
    print(f"Candidate hint seed: {RANDOM_SEED}")
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
    assert "seed_stability" not in initial_result.diagnostics.applied_soft_constraints
    solver_floor_plan_stages.append(
        make_floor_plan_stage(
            stage="initial_generation",
            feature="floor_plan_solver",
            profile=initial_result.profile_name,
            status=initial_result.status.value,
            floor_plan=initial_floor_plan,
        )
    )
    print_solver_stage_result(initial_result)

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
    assert "seed_stability" in refinement_a_result.diagnostics.applied_soft_constraints
    assert_refinement_respects_seed_policy(
        initial_floor_plan,
        refinement_a_floor_plan,
        refinement_a_profile,
    )
    solver_floor_plan_stages.append(
        make_floor_plan_stage(
            stage="refinement_a",
            feature="floor_plan_solver",
            profile=refinement_a_result.profile_name,
            status=refinement_a_result.status.value,
            floor_plan=refinement_a_floor_plan,
        )
    )
    print_solver_stage_result(refinement_a_result)

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
    assert "seed_stability" in refinement_b_result.diagnostics.applied_soft_constraints
    assert_refinement_respects_seed_policy(
        refinement_a_floor_plan,
        refinement_b_floor_plan,
        refinement_b_profile,
    )
    solver_floor_plan_stages.append(
        make_floor_plan_stage(
            stage="refinement_b",
            feature="floor_plan_solver",
            profile=refinement_b_result.profile_name,
            status=refinement_b_result.status.value,
            floor_plan=refinement_b_floor_plan,
        )
    )
    print_solver_stage_result(refinement_b_result)

    assert len(solver_floor_plan_stages) == 3
    assert [stage["stage"] for stage in solver_floor_plan_stages] == [
        "initial_generation",
        "refinement_a",
        "refinement_b",
    ]

    # Post processing mutates the FloorPlan supplied in its request. Pass a
    # deep copy so Refinement B remains an unchanged solver output and the
    # solver visualization history stays trustworthy.
    post_processing_input = copy.deepcopy(refinement_b_floor_plan)
    post_processing_input_snapshot = copy.deepcopy(post_processing_input)
    post_processing_request = PostProcessingRequest(
        floor_plan=post_processing_input,
        profile=POST_PROCESSING_INITIAL_GENERATION_PROFILE,
        specification=specification,
        request_id=REQUEST_ID,
    )
    post_processing_result = post_process_floor_plan(post_processing_request)
    post_processed_floor_plan = validate_post_processing_result(
        post_processing_result,
        specification,
        expected_processor_count=len(
            POST_PROCESSING_INITIAL_GENERATION_PROFILE.processors
        ),
    )
    post_processing_floor_plan_stages.append(
        make_floor_plan_stage(
            stage="post_processing",
            feature="floor_plan_post_processing",
            profile=POST_PROCESSING_INITIAL_GENERATION_PROFILE.name,
            status=post_processing_result.status.value,
            floor_plan=post_processed_floor_plan,
        )
    )
    print_post_processing_result(post_processing_result)

    assert len(post_processing_floor_plan_stages) == 1
    assert post_processing_floor_plan_stages[0]["stage"] == "post_processing"
    assert solver_floor_plan_stages[-1]["floor_plan"] == refinement_b_floor_plan, (
        "Post processing unexpectedly modified the stored Refinement B snapshot."
    )

    output_path = save_flow_output(
        specification=specification,
        candidate_hints=candidate_hints,
        solver_floor_plan_stages=solver_floor_plan_stages,
        post_processing_floor_plan_stages=post_processing_floor_plan_stages,
        initial_request=initial_request,
        initial_result=initial_result,
        refinement_a_request=refinement_a_request,
        refinement_a_result=refinement_a_result,
        refinement_b_request=refinement_b_request,
        refinement_b_result=refinement_b_result,
        post_processing_input_snapshot=post_processing_input_snapshot,
        post_processing_request=post_processing_request,
        post_processing_result=post_processing_result,
    )

    visualization = build_visualization_flow(
        solver_floor_plan_stages=solver_floor_plan_stages,
        post_processing_floor_plan_stages=post_processing_floor_plan_stages,
    )

    visualization_output = render_floor_plan_general(
        visualization,
        output_prefix="solver_post_process_flow",
    )

    print("\n" + "#" * 78)
    print("SOLVER -> POST PROCESSING FLOW CHECK PASSED")
    print("#" * 78)
    print("Initial generation, Refinement A, and Refinement B completed.")
    print("Refinement B output was accepted directly by post processing.")
    print("Solver and post-processing floor-plan stage snapshots were preserved.")
    print(f"Combined JSON output: {output_path}")
    print(f"Visualization image: {visualization_output}")


def build_visualization_flow(
    *,
    solver_floor_plan_stages: list[FloorPlanStage],
    post_processing_floor_plan_stages: list[FloorPlanStage],
) -> FloorPlanFlowVisualization:
    """Convert flow-test stage snapshots into the visualization contract."""

    stages: list[FloorPlanVisualizationStage] = []

    for stage in solver_floor_plan_stages:
        stages.append(
            FloorPlanVisualizationStage(
                stage_id=stage["stage"],
                stage_name=stage["stage"].replace("_", " ").title(),
                category="solver",
                profile_name=stage["profile"],
                floor_plan=copy.deepcopy(stage["floor_plan"]),
            )
        )

    for stage in post_processing_floor_plan_stages:
        stages.append(
            FloorPlanVisualizationStage(
                stage_id=stage["stage"],
                stage_name=stage["stage"].replace("_", " ").title(),
                category="post_processing",
                profile_name=stage["profile"],
                floor_plan=copy.deepcopy(stage["floor_plan"]),
            )
        )

    return FloorPlanFlowVisualization(
        stages=tuple(stages),
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import math
from dataclasses import dataclass

from app.algorithms.floor_plan_solver import FloorPlanSolveResult, GenerationProfile
from app.algorithms.types_new.floor_plan import FloorPlan, FloorPlanRoom, Polygon
from app.algorithms.types_new.floor_plan_spec import (
    ConstraintStrength,
    FloorPlanGenerationSpec,
    MatchPolicy,
    RoomType,
)

EPSILON = 1e-7


@dataclass(frozen=True, slots=True)
class RectangleBounds:
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center_y(self) -> float:
        return (self.min_y + self.max_y) / 2


def _approximately_equal(first: float, second: float) -> bool:
    return math.isclose(first, second, abs_tol=EPSILON)


def rectangle_bounds(polygon: Polygon) -> RectangleBounds:
    points = tuple(polygon.points)
    assert len(points) == 4, "Solver rooms must be four-point rectangles"

    xs = {round(float(point.x), 7) for point in points}
    ys = {round(float(point.y), 7) for point in points}
    assert len(xs) == 2, "Rectangle must have exactly two x coordinates"
    assert len(ys) == 2, "Rectangle must have exactly two y coordinates"

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    expected_corners = {
        (min_x, min_y),
        (max_x, min_y),
        (max_x, max_y),
        (min_x, max_y),
    }
    actual_corners = {
        (round(float(point.x), 7), round(float(point.y), 7))
        for point in points
    }
    assert actual_corners == expected_corners, "Polygon must be axis-aligned"
    assert max_x > min_x and max_y > min_y, "Rectangle cannot be empty"

    return RectangleBounds(min_x, min_y, max_x, max_y)


def room_map(floor_plan: FloorPlan) -> dict[str, FloorPlanRoom]:
    return {str(room.id): room for room in floor_plan.rooms}


def assert_solved_result(result: FloorPlanSolveResult, profile_name: str) -> FloorPlan:
    assert result.solved, (
        f"Expected profile '{profile_name}' to solve, got "
        f"{result.status.value}: {result.message}"
    )
    assert result.floor_plan is not None
    assert result.profile_name == profile_name
    assert result.diagnostics.raw_status
    assert result.diagnostics.wall_time_seconds >= 0
    assert result.diagnostics.conflicts >= 0
    assert result.diagnostics.branches >= 0
    return result.floor_plan


def assert_floor_plan_contract(
    floor_plan: FloorPlan,
    specification: FloorPlanGenerationSpec,
) -> None:
    floor_bounds = rectangle_bounds(floor_plan.boundary)
    assert _approximately_equal(floor_bounds.min_x, 0)
    assert _approximately_equal(floor_bounds.min_y, 0)
    assert _approximately_equal(floor_bounds.width, specification.floor.width)
    assert _approximately_equal(floor_bounds.height, specification.floor.height)

    expected_required_ids = {
        str(room.id) for room in specification.rooms if room.required
    }
    actual_ids = [str(room.id) for room in floor_plan.rooms]
    assert len(actual_ids) == len(set(actual_ids)), "Room ids must be unique"
    assert expected_required_ids.issubset(set(actual_ids))

    for room in floor_plan.rooms:
        assert room.name.strip()
        bounds = rectangle_bounds(room.boundary)
        assert bounds.min_x >= floor_bounds.min_x - EPSILON
        assert bounds.min_y >= floor_bounds.min_y - EPSILON
        assert bounds.max_x <= floor_bounds.max_x + EPSILON
        assert bounds.max_y <= floor_bounds.max_y + EPSILON

    assert floor_plan.openings == [], (
        "The solver stage must not generate doors or windows; openings belong "
        "to the later openings feature"
    )


def assert_room_size_contract(
    floor_plan: FloorPlan,
    specification: FloorPlanGenerationSpec,
) -> None:
    specs_by_id = {str(room.id): room for room in specification.rooms}
    for room in floor_plan.rooms:
        spec = specs_by_id[str(room.id)]
        bounds = rectangle_bounds(room.boundary)
        assert spec.size.min_width - EPSILON <= bounds.width <= spec.size.max_width + EPSILON
        assert spec.size.min_height - EPSILON <= bounds.height <= spec.size.max_height + EPSILON
        assert spec.size.min_area - EPSILON <= bounds.area <= spec.size.max_area + EPSILON


def overlap_area(first: RectangleBounds, second: RectangleBounds) -> float:
    width = max(0.0, min(first.max_x, second.max_x) - max(first.min_x, second.min_x))
    height = max(0.0, min(first.max_y, second.max_y) - max(first.min_y, second.min_y))
    return width * height


def assert_rooms_do_not_overlap(floor_plan: FloorPlan) -> None:
    rooms = tuple(floor_plan.rooms)
    for index, first in enumerate(rooms):
        first_bounds = rectangle_bounds(first.boundary)
        for second in rooms[index + 1 :]:
            second_bounds = rectangle_bounds(second.boundary)
            assert overlap_area(first_bounds, second_bounds) <= EPSILON, (
                f"Rooms '{first.id}' and '{second.id}' overlap"
            )


def shared_wall_length(first: RectangleBounds, second: RectangleBounds) -> float:
    shared = 0.0
    if _approximately_equal(first.max_x, second.min_x) or _approximately_equal(
        first.min_x, second.max_x
    ):
        shared = max(
            shared,
            max(0.0, min(first.max_y, second.max_y) - max(first.min_y, second.min_y)),
        )
    if _approximately_equal(first.max_y, second.min_y) or _approximately_equal(
        first.min_y, second.max_y
    ):
        shared = max(
            shared,
            max(0.0, min(first.max_x, second.max_x) - max(first.min_x, second.min_x)),
        )
    return shared


def assert_hard_room_relations(
    floor_plan: FloorPlan,
    specification: FloorPlanGenerationSpec,
    *,
    minimum_overlap: float,
) -> None:
    rooms = room_map(floor_plan)
    for relation in specification.room_relations:
        if relation.strength is not ConstraintStrength.HARD:
            continue
        source = rooms.get(str(relation.source_room_id))
        if source is None:
            continue
        source_bounds = rectangle_bounds(source.boundary)
        adjacency_results = []
        for target_id in relation.target_room_ids:
            target = rooms.get(str(target_id))
            adjacency_results.append(
                target is not None
                and shared_wall_length(
                    source_bounds,
                    rectangle_bounds(target.boundary),
                )
                >= minimum_overlap - EPSILON
            )

        if relation.match_policy is MatchPolicy.AND:
            assert all(adjacency_results), (
                f"Hard AND relation failed for room '{relation.source_room_id}'"
            )
        else:
            assert any(adjacency_results), (
                f"Hard OR relation failed for room '{relation.source_room_id}'"
            )


def assert_minimum_coverage(
    floor_plan: FloorPlan,
    specification: FloorPlanGenerationSpec,
    *,
    minimum_ratio: float,
) -> None:
    occupied_area = sum(
        rectangle_bounds(room.boundary).area for room in floor_plan.rooms
    )
    floor_area = specification.floor.width * specification.floor.height
    assert occupied_area / floor_area >= minimum_ratio - EPSILON


def assert_hallway_connectivity(floor_plan: FloorPlan) -> None:
    hallways = [room for room in floor_plan.rooms if room.room_type is RoomType.HALLWAY]
    living_rooms = [
        room for room in floor_plan.rooms if room.room_type is RoomType.LIVING_ROOM
    ]
    destinations = [
        room
        for room in floor_plan.rooms
        if room.room_type not in {RoomType.HALLWAY, RoomType.LIVING_ROOM}
    ]

    for hallway in hallways:
        hallway_bounds = rectangle_bounds(hallway.boundary)
        assert any(
            shared_wall_length(hallway_bounds, rectangle_bounds(room.boundary)) > 0
            for room in living_rooms
        )
        assert any(
            shared_wall_length(hallway_bounds, rectangle_bounds(room.boundary)) > 0
            for room in destinations
        )


def assert_front_rules(floor_plan: FloorPlan) -> None:
    rooms = tuple(floor_plan.rooms)
    verandas = [room for room in rooms if room.room_type is RoomType.VERANDA]
    if verandas:
        anchor = verandas[0]
    else:
        living_rooms = [room for room in rooms if room.room_type is RoomType.LIVING_ROOM]
        if not living_rooms:
            return
        anchor = living_rooms[0]

    anchor_bounds = rectangle_bounds(anchor.boundary)
    if anchor.room_type is RoomType.VERANDA:
        assert _approximately_equal(anchor_bounds.min_y, 0.0)

    for room in rooms:
        if room.id == anchor.id:
            continue
        assert anchor_bounds.center_y <= rectangle_bounds(room.boundary).center_y + EPSILON


def assert_whole_project_unit_grid(floor_plan: FloorPlan) -> None:
    """Enforce the project rule that one unit is 10 cm and decimals are invalid."""

    polygons = [floor_plan.boundary, *(room.boundary for room in floor_plan.rooms)]
    for polygon in polygons:
        for point in polygon.points:
            assert _approximately_equal(point.x, round(point.x)), (
                f"x={point.x} is below the project's 10 cm unit resolution"
            )
            assert _approximately_equal(point.y, round(point.y)), (
                f"y={point.y} is below the project's 10 cm unit resolution"
            )


def assert_refinement_stays_within_seed_policy(
    previous: FloorPlan,
    refined: FloorPlan,
    profile: GenerationProfile,
) -> None:
    previous_rooms = room_map(previous)
    refined_rooms = room_map(refined)
    assert set(previous_rooms) == set(refined_rooms)

    scale = profile.preparation.coordinate_scale

    def effective_tolerance(value: float | None) -> float | None:
        if value is None:
            return None
        scaled = math.ceil(value * scale - 1e-9)
        return scaled / scale

    position_tolerance = effective_tolerance(profile.seed.position_tolerance)
    size_tolerance = effective_tolerance(profile.seed.size_tolerance)
    for room_id, previous_room in previous_rooms.items():
        old = rectangle_bounds(previous_room.boundary)
        new = rectangle_bounds(refined_rooms[room_id].boundary)
        if position_tolerance is not None:
            assert abs(new.min_x - old.min_x) <= position_tolerance + EPSILON
            assert abs(new.min_y - old.min_y) <= position_tolerance + EPSILON
        if size_tolerance is not None:
            assert abs(new.width - old.width) <= size_tolerance + EPSILON
            assert abs(new.height - old.height) <= size_tolerance + EPSILON

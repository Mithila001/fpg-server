from __future__ import annotations

from app.algorithms.floor_plan_openings.analysis import analyze_floor_plan
from app.algorithms.floor_plan_openings.profiles import DEFAULT_OPENING_PROFILE
from app.algorithms.floor_plan_openings.validation import validate_request_floor_plan
from app.algorithms.floor_plan_openings.exceptions import OpeningInputError
from app.algorithms.types_new import FloorPlan, RoomType
import pytest

from .conftest import rectangle, room


def test_partial_shared_wall_is_noded_without_turning_gap_into_exterior() -> None:
    plan = FloorPlan(
        rectangle(0, 0, 30, 20),
        [
            room("left", RoomType.LIVING_ROOM, rectangle(0, 0, 10, 20)),
            room("right", RoomType.KITCHEN, rectangle(10, 0, 20, 10)),
        ],
    )
    validate_request_floor_plan(plan, DEFAULT_OPENING_PROFILE)
    prepared = analyze_floor_plan(plan, DEFAULT_OPENING_PROFILE)

    shared = [wall for wall in prepared.walls if wall.kind.value == "shared"]
    assert len(shared) == 1
    assert shared[0].length == 100
    assert not any(
        wall.kind.value == "exterior"
        and wall.orientation.value == "vertical"
        and wall.fixed_coordinate == 100
        and wall.start >= 100
        for wall in prepared.walls
    )


def test_internal_gap_facing_edge_is_not_an_exterior_wall() -> None:
    plan = FloorPlan(
        rectangle(0, 0, 30, 20),
        [room("living", RoomType.LIVING_ROOM, rectangle(0, 0, 10, 20))],
    )
    validate_request_floor_plan(plan, DEFAULT_OPENING_PROFILE)
    prepared = analyze_floor_plan(plan, DEFAULT_OPENING_PROFILE)
    assert not any(
        wall.kind.value == "exterior"
        and wall.orientation.value == "vertical"
        and wall.fixed_coordinate == 100
        for wall in prepared.walls
    )


def test_wall_ids_and_analysis_order_are_deterministic() -> None:
    plan = FloorPlan(
        rectangle(0, 0, 20, 20),
        [room("living", RoomType.LIVING_ROOM, rectangle(0, 0, 20, 20))],
    )
    first = analyze_floor_plan(plan, DEFAULT_OPENING_PROFILE)
    second = analyze_floor_plan(plan, DEFAULT_OPENING_PROFILE)
    assert first.walls == second.walls


def test_reversed_polygon_winding_is_rejected_as_noncanonical() -> None:
    boundary = rectangle(0, 0, 20, 20)
    reversed_boundary = type(boundary)(tuple(reversed(boundary.points)))
    plan = FloorPlan(
        reversed_boundary,
        [room("living", RoomType.LIVING_ROOM, rectangle(0, 0, 20, 20))],
    )
    with pytest.raises(OpeningInputError, match="canonical"):
        validate_request_floor_plan(plan, DEFAULT_OPENING_PROFILE)

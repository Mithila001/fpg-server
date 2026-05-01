from __future__ import annotations

from app.algorithms.types.base import WallSegmentPayload
from app.algorithms.types.domain import ProcessedRoomData
from app.algorithms.types.openings import FloorPlanWithOpenings, OpeningData
from app.util.algorithm_manager.fpg_procesors.union_floor_plan import (
    union_floor_plan,
)


def _room(
    name: str,
    room_type: str,
    x: float,
    y: float,
    x_end: float,
    y_end: float,
    original_index: int = 0,
) -> ProcessedRoomData:
    return ProcessedRoomData(
        type=room_type,
        name=name,
        original_index=original_index,
        vertices=[
            (x, y),
            (x_end, y),
            (x_end, y_end),
            (x, y_end),
        ],
        area=(x_end - x) * (y_end - y),
    )


def _opening() -> OpeningData:
    return OpeningData(
        room_name="living1",
        room_type="livingRoom",
        opening_type="mainDoor",
        side="south",
        x1=1.0,
        y1=0.0,
        x2=3.0,
        y2=0.0,
        connected_room_name="veranda1",
        connected_room_type="veranda",
    )


def _segment_tuple(segment: WallSegmentPayload) -> tuple[float, float, float, float]:
    return (segment["x1"], segment["y1"], segment["x2"], segment["y2"])


def test_union_floor_plan_returns_empty_walls_for_empty_input() -> None:
    floor_plan = FloorPlanWithOpenings(floor_plan=[], openings=[_opening()])

    result = union_floor_plan(floor_plan)

    assert result["floor_plan_with_openings"] == floor_plan
    assert result["unified_floor_plan"]["walls"] == []
    assert result["unified_floor_plan"]["total_wall_length"] == 0.0


def test_union_floor_plan_merges_single_room_to_outer_boundary() -> None:
    floor_plan = FloorPlanWithOpenings(
        floor_plan=[_room("room1", "bedroom", 0.0, 0.0, 10.0, 8.0)],
        openings=[_opening()],
    )

    result = union_floor_plan(floor_plan)
    walls = result["unified_floor_plan"]["walls"]

    assert result["floor_plan_with_openings"] == floor_plan
    assert len(walls) == 4
    assert {_segment_tuple(segment) for segment in walls} == {
        (0.0, 0.0, 0.0, 8.0),
        (0.0, 0.0, 10.0, 0.0),
        (0.0, 8.0, 10.0, 8.0),
        (10.0, 0.0, 10.0, 8.0),
    }


def test_union_floor_plan_preserves_shared_wall_for_touching_rooms() -> None:
    floor_plan = FloorPlanWithOpenings(
        floor_plan=[
            _room("room1", "bedroom", 0.0, 0.0, 10.0, 10.0, 0),
            _room("room2", "kitchen", 10.0, 0.0, 20.0, 10.0, 1),
        ],
        openings=[_opening()],
    )

    result = union_floor_plan(floor_plan)
    walls = result["unified_floor_plan"]["walls"]

    assert len(walls) == 6
    assert {_segment_tuple(segment) for segment in walls} == {
        (0.0, 0.0, 0.0, 10.0),
        (0.0, 0.0, 10.0, 0.0),
        (0.0, 10.0, 10.0, 10.0),
        (10.0, 0.0, 20.0, 0.0),
        (10.0, 10.0, 20.0, 10.0),
        (20.0, 0.0, 20.0, 10.0),
    }
    assert result["unified_floor_plan"]["total_wall_length"] == 60.0


def test_union_floor_plan_merges_overlapping_rooms_into_l_shape_boundary() -> None:
    floor_plan = FloorPlanWithOpenings(
        floor_plan=[
            _room("room1", "bedroom", 0.0, 0.0, 10.0, 10.0, 0),
            _room("room2", "kitchen", 5.0, 5.0, 15.0, 15.0, 1),
        ],
        openings=[_opening()],
    )

    result = union_floor_plan(floor_plan)
    walls = result["unified_floor_plan"]["walls"]

    assert len(walls) >= 8
    assert result["unified_floor_plan"]["total_wall_length"] >= 60.0

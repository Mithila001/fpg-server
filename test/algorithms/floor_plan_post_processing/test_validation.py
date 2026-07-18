from __future__ import annotations

from app.algorithms.floor_plan_post_processing import (
    INITIAL_GENERATION_PROFILE,
    PipelineStatus,
    PostProcessingRequest,
    post_process_floor_plan,
)
from app.algorithms.types_new import (
    FloorPlan,
    FloorPlanOpening,
    OpeningId,
    OpeningPurpose,
    OpeningType,
    Point,
    RoomId,
    RoomType,
)

from .conftest import rectangle, room


def test_rejects_duplicate_ids_and_overlapping_standard_rooms():
    duplicate = FloorPlan(
        rectangle(0, 0, 20, 20),
        [
            room("same", RoomType.BEDROOM, rectangle(0, 0, 5, 5)),
            room("same", RoomType.KITCHEN, rectangle(10, 10, 15, 15)),
        ],
    )
    overlap = FloorPlan(
        rectangle(0, 0, 20, 20),
        [
            room("a", RoomType.BEDROOM, rectangle(0, 0, 10, 10)),
            room("b", RoomType.KITCHEN, rectangle(5, 5, 15, 15)),
        ],
    )
    assert (
        post_process_floor_plan(
            PostProcessingRequest(duplicate, INITIAL_GENERATION_PROFILE)
        ).status
        is PipelineStatus.FAILED
    )
    assert (
        post_process_floor_plan(
            PostProcessingRequest(overlap, INITIAL_GENERATION_PROFILE)
        ).status
        is PipelineStatus.FAILED
    )


def test_geometry_profile_rejects_existing_openings():
    plan = FloorPlan(
        rectangle(0, 0, 20, 20),
        [room("bed", RoomType.BEDROOM, rectangle(0, 0, 10, 10))],
        [
            FloorPlanOpening(
                OpeningId("door"),
                OpeningType.DOOR,
                OpeningPurpose.ROOM_CONNECTION,
                Point(0, 1),
                Point(0, 2),
                (RoomId("bed"),),
            )
        ],
    )
    result = post_process_floor_plan(
        PostProcessingRequest(plan, INITIAL_GENERATION_PROFILE)
    )
    assert result.status is PipelineStatus.FAILED
    assert result.failure is not None
    assert result.failure.code == "validation_failed"


def test_rejects_noncanonical_closed_polygon_ring():
    closed = rectangle(0, 0, 10, 10)
    closed = type(closed)(closed.points + (closed.points[0],))
    plan = FloorPlan(
        rectangle(0, 0, 20, 20),
        [room("bed", RoomType.BEDROOM, closed)],
    )
    result = post_process_floor_plan(
        PostProcessingRequest(plan, INITIAL_GENERATION_PROFILE)
    )
    assert result.status is PipelineStatus.FAILED
    assert result.failure is not None
    assert result.failure.code == "validation_failed"

from __future__ import annotations

import pytest

from app.algorithms.types_new import (
    FloorPlan,
    FloorPlanRoom,
    Point,
    Polygon,
    RoomId,
    RoomRole,
    RoomType,
)


def polygon(*coordinates: tuple[float, float]) -> Polygon:
    return Polygon(tuple(Point(x, y) for x, y in coordinates))


def rectangle(x1: float, y1: float, x2: float, y2: float) -> Polygon:
    return polygon((x1, y1), (x2, y1), (x2, y2), (x1, y2))


def room(
    room_id: str,
    room_type: RoomType,
    boundary: Polygon,
    *,
    role: RoomRole = RoomRole.STANDARD,
    parent_room_id: str | None = None,
) -> FloorPlanRoom:
    return FloorPlanRoom(
        RoomId(room_id),
        room_type,
        room_id,
        boundary,
        role,
        RoomId(parent_room_id) if parent_room_id else None,
    )


@pytest.fixture
def empty_plan() -> FloorPlan:
    return FloorPlan(rectangle(0, 0, 30, 30), [])

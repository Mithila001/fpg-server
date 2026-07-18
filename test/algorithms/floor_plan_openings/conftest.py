from __future__ import annotations

from app.algorithms.types_new import (
    FloorPlan,
    FloorPlanRoom,
    Point,
    Polygon,
    RoomId,
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
) -> FloorPlanRoom:
    return FloorPlanRoom(RoomId(room_id), room_type, room_id, boundary)


def two_room_plan() -> FloorPlan:
    return FloorPlan(
        rectangle(0, 0, 30, 20),
        [
            room("living", RoomType.LIVING_ROOM, rectangle(0, 0, 15, 20)),
            room("kitchen", RoomType.KITCHEN, rectangle(15, 0, 30, 20)),
        ],
    )

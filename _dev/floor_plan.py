from dataclasses import dataclass, field
from enum import Enum
from typing import NewType
from _dev.floor_plan_spec import RoomId, RoomType



OpeningId = NewType("OpeningId", str)


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class Polygon:
    points: tuple[Point, ...]


class OpeningType(str, Enum):
    DOOR = "door"
    WINDOW = "window"


@dataclass
class FloorPlanRoom:
    id: RoomId
    room_type: RoomType
    name: str
    boundary: Polygon


@dataclass
class FloorPlanOpening:
    id: OpeningId
    opening_type: OpeningType
    start: Point
    end: Point
    connected_room_ids: tuple[RoomId, ...] = ()


@dataclass
class FloorPlan:
    boundary: Polygon
    rooms: list[FloorPlanRoom]
    openings: list[FloorPlanOpening] = field(default_factory=list)
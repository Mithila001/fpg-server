from __future__ import annotations

from typing import NotRequired, TypedDict

from .geometry import OpeningPayload, PointPayload, RoomBoundaryPayload, WallSegmentPayload
from .processor_outputs import CompactRoomPayload, WallUnionResultPayload


class PostProcessInputPayload(TypedDict):
    rooms: list[RoomBoundaryPayload]
    openings: list[OpeningPayload]
    tolerance: NotRequired[float]
    wall_union: NotRequired[WallUnionResultPayload]


class VerandaMetadataPayload(TypedDict):
    room_name: str
    l_veranda_pillar: PointPayload
    r_veranda_pillar: PointPayload
    veranda_back_points: list[PointPayload]


class PostProcessMetadataPayload(TypedDict):
    veranda: VerandaMetadataPayload | None
    garage_shared_horizontal_overlap_segment: WallSegmentPayload | None
    hallway_living_shared_walls: list[WallSegmentPayload]
    converted_hallway_living_openings: int


class RoomOutputPayload(TypedDict):
    room_name: str
    room_type: str
    room_walls: list[WallSegmentPayload]


class DoorPayload(TypedDict):
    room1_name: str
    room1_type: str
    room2_name: str
    room2_type: str
    opening_type: str
    x1: float
    y1: float
    x2: float
    y2: float


class WindowPayload(TypedDict):
    room_name: str
    room_type: str
    opening_type: str
    x1: float
    y1: float
    x2: float
    y2: float


class PostProcessOutputPayload(TypedDict):
    status: str
    message: str
    union_walls: list[WallSegmentPayload]
    rooms: dict[str, RoomOutputPayload]
    doors: list[DoorPayload]
    windows: list[WindowPayload]


class QuickPostProcessOutputPayload(TypedDict):
    status: str
    message: str
    rooms: list[RoomBoundaryPayload]
    wall_union: WallUnionResultPayload
    openings: NotRequired[list[OpeningPayload]]

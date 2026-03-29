from __future__ import annotations

from typing import NotRequired, TypedDict

from .geometry import OpeningPayload, RoomBoundaryPayload, WallSegmentPayload
from .processor_outputs import CompactRoomPayload, WallUnionResultPayload


class PostProcessInputPayload(TypedDict):
    rooms: list[RoomBoundaryPayload]
    openings: list[OpeningPayload]
    tolerance: NotRequired[float]
    wall_union: NotRequired[WallUnionResultPayload]


class PostProcessOutputPayload(TypedDict):
    status: str
    message: str
    walls: list[WallSegmentPayload]
    compact_by_room: dict[str, CompactRoomPayload]


class QuickPostProcessOutputPayload(TypedDict):
    status: str
    message: str
    rooms: list[RoomBoundaryPayload]
    wall_union: WallUnionResultPayload

from __future__ import annotations

from typing import NotRequired, TypedDict

from .geometry import OpeningPayload, RoomBoundaryPayload, WallSegmentPayload
from .processor_outputs import CompactRoomPayload


class PostProcessInputPayload(TypedDict):
    rooms: list[RoomBoundaryPayload]
    openings: list[OpeningPayload]
    tolerance: NotRequired[float]


class PostProcessOutputPayload(TypedDict):
    status: str
    message: str
    walls: list[WallSegmentPayload]
    compact_by_room: dict[str, CompactRoomPayload]

from __future__ import annotations

from typing import TypedDict

from .geometry import OpeningPayload, WallSegmentPayload


class RoomWallsPayload(TypedDict):
    room_name: str
    room_type: str
    walls: list[WallSegmentPayload]


class WallUnionResultPayload(TypedDict):
    walls: list[WallSegmentPayload]
    room_walls: dict[str, RoomWallsPayload]


class CompactRoomPayload(TypedDict):
    room_name: str
    room_type: str
    walls: list[WallSegmentPayload]
    openings: list[OpeningPayload]

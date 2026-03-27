from __future__ import annotations

from typing import NotRequired, TypedDict


class WallSegmentPayload(TypedDict):
    x1: float
    y1: float
    x2: float
    y2: float


class RoomBoundaryPayload(TypedDict):
    name: str
    type: str
    x: float
    y: float
    x_end: float
    y_end: float


class OpeningPayload(TypedDict):
    room_name: str
    room_type: NotRequired[str]
    opening_type: NotRequired[str]
    side: NotRequired[str]
    x1: NotRequired[float]
    y1: NotRequired[float]
    x2: NotRequired[float]
    y2: NotRequired[float]
    connected_room_name: NotRequired[str]
    connected_room_type: NotRequired[str]

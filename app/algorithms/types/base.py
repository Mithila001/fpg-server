from __future__ import annotations

from typing import TypedDict


class PointPayload(TypedDict):
    x: float
    y: float


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

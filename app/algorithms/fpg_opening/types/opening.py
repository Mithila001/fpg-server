from __future__ import annotations

from typing import Any, Literal, TypedDict


OpeningSide = Literal["south", "east", "north", "west"]


class NormalizedRoom(TypedDict):
    name: str
    type: str
    x: float
    y: float
    x_end: float
    y_end: float


class OpeningPayload(TypedDict):
    room_name: str
    room_type: str
    opening_type: str
    side: OpeningSide
    x1: float
    y1: float
    x2: float
    y2: float


class OpeningRunResult(TypedDict):
    status: str
    message: str
    openings: list[OpeningPayload]
    warnings: list[str]


RoomInput = dict[str, Any]

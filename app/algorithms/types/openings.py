from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, NotRequired, TypedDict

from app.algorithms.types.domain import ProcessedRoomData


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
    room_type: NotRequired[str]
    opening_type: NotRequired[str]
    side: NotRequired[str]
    x1: NotRequired[float]
    y1: NotRequired[float]
    x2: NotRequired[float]
    y2: NotRequired[float]
    connected_room_name: NotRequired[str]
    connected_room_type: NotRequired[str]


class OpeningRunResult(TypedDict):
    status: str
    message: str
    openings: list[OpeningPayload]
    warnings: list[str]


@dataclass
class FloorPlanWithOpenings:
    floor_plan: list[ProcessedRoomData]
    openings: list[OpeningData]


@dataclass
class OpeningData:
    room_name: str
    room_type: str
    opening_type: str
    side: str
    x1: float
    y1: float
    x2: float
    y2: float
    connected_room_name: str
    connected_room_type: str


RoomInput = dict[str, Any]

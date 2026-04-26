from __future__ import annotations

from typing import NotRequired, TypedDict

from .base import PointPayload, RoomBoundaryPayload, WallSegmentPayload
from .openings import OpeningPayload


class ProcessContextPayload(TypedDict):
    """Pipeline context for processing stages."""

    rooms: list[RoomBoundaryPayload]
    openings: list[OpeningPayload]
    tolerance: float
    wall_union: NotRequired[dict]


class RoomWallsPayload(TypedDict):
    """Room walls for post-processing."""

    room_name: str
    room_type: str
    walls: list[WallSegmentPayload]


class WallUnionResultPayload(TypedDict):
    """Result of wall union operation."""

    walls: list[WallSegmentPayload]
    room_walls: dict[str, RoomWallsPayload]


class CompactRoomPayload(TypedDict):
    """Compacted room representation."""

    room_name: str
    room_type: str
    walls: list[WallSegmentPayload]
    openings: list[OpeningPayload]


class PostProcessInputPayload(TypedDict):
    """Input to post-processing stage."""

    rooms: list[RoomBoundaryPayload]
    openings: list[OpeningPayload]
    tolerance: NotRequired[float]
    wall_union: NotRequired[WallUnionResultPayload]


class VerandaMetadataPayload(TypedDict):
    """Veranda-specific metadata."""

    room_name: str
    l_veranda_pillar: PointPayload
    r_veranda_pillar: PointPayload
    veranda_back_points: list[PointPayload]


class PostProcessMetadataPayload(TypedDict):
    """Metadata collected during post-processing."""

    veranda: VerandaMetadataPayload | None
    garage_shared_horizontal_overlap_segment: WallSegmentPayload | None
    hallway_living_shared_walls: list[WallSegmentPayload]
    converted_hallway_living_openings: int


class RoomOutputPayload(TypedDict):
    """Output room representation."""

    room_name: str
    room_type: str
    room_walls: list[WallSegmentPayload]


class DoorPayload(TypedDict):
    """Door opening representation."""

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
    """Window opening representation."""

    room_name: str
    room_type: str
    opening_type: str
    x1: float
    y1: float
    x2: float
    y2: float


class PostProcessOutputPayload(TypedDict):
    """Output from post-processing stage."""

    status: str
    message: str
    union_walls: list[WallSegmentPayload]
    rooms: dict[str, RoomOutputPayload]
    doors: list[DoorPayload]
    windows: list[WindowPayload]


class QuickPostProcessOutputPayload(TypedDict):
    """Quick post-processing output (minimal processing)."""

    status: str
    message: str
    rooms: list[RoomBoundaryPayload]
    wall_union: WallUnionResultPayload
    openings: NotRequired[list[OpeningPayload]]

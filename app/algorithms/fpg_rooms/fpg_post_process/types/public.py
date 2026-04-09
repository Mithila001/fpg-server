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


class PostProcessOutputPayload(TypedDict):
    status: str
    message: str
    walls: list[WallSegmentPayload]
    compact_by_room: dict[str, CompactRoomPayload]
    metadata: PostProcessMetadataPayload


class QuickPostProcessOutputPayload(TypedDict):
    status: str
    message: str
    rooms: list[RoomBoundaryPayload]
    wall_union: WallUnionResultPayload

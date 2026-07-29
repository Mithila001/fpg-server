from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.algorithms.types_new import RoomType
from app.generation_metadata import (
    FLOOR_AREA_BUFFER,
    HALLWAY_AREA_BUFFER,
    HALLWAY_COUNT,
)


class RoomSizeSelectionStrategy(str, Enum):
    MAJORITY = "majority"


class ExcessAttachedBathroomPolicy(str, Enum):
    REMOVE = "remove"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class PreprocessingPolicy:
    mandatory_room_types: tuple[RoomType, ...] = (
        RoomType.BEDROOM,
        RoomType.KITCHEN,
        RoomType.BATHROOM,
        RoomType.LIVING_ROOM,
        RoomType.DINING_ROOM,
        RoomType.VERANDA,
    )
    min_aspect_ratio: float = 0.5
    max_aspect_ratio: float = 2.0
    floor_area_buffer: float = FLOOR_AREA_BUFFER
    hallway_area_buffer: float = HALLWAY_AREA_BUFFER
    default_room_size: str = "regular"
    room_size_strategy: RoomSizeSelectionStrategy = RoomSizeSelectionStrategy.MAJORITY
    size_normalization_exclusions: tuple[RoomType, ...] = (RoomType.HALLWAY,)
    excess_attached_bathrooms: ExcessAttachedBathroomPolicy = (
        ExcessAttachedBathroomPolicy.REJECT
    )
    hallway_count: int = HALLWAY_COUNT
    hallway_min_width: float = 10.0

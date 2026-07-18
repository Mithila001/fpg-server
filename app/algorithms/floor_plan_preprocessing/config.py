from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.algorithms.types_new import RoomType


class RoomSizeSelectionStrategy(str, Enum):
    MAJORITY = "majority"


class ExcessAttachedBathroomPolicy(str, Enum):
    REMOVE = "remove"
    REJECT = "reject"


class OptionalRoomFailurePolicy(str, Enum):
    REMOVE = "remove"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class PreprocessingPolicy:
    mandatory_room_types: tuple[RoomType, ...] = (
        RoomType.BEDROOM,
        RoomType.KITCHEN,
        RoomType.BATHROOM,
        RoomType.VERANDA,
    )
    optional_room_types: tuple[RoomType, ...] = (
        RoomType.GARAGE,
        RoomType.ATTACHED_BATHROOM,
        RoomType.DINING_ROOM,
    )
    min_aspect_ratio: float = 0.5
    max_aspect_ratio: float = 2.0
    floor_area_buffer: float = 500.0
    default_room_size: str = "regular"
    room_size_strategy: RoomSizeSelectionStrategy = RoomSizeSelectionStrategy.MAJORITY
    size_normalization_exclusions: tuple[RoomType, ...] = (RoomType.HALLWAY,)
    excess_attached_bathrooms: ExcessAttachedBathroomPolicy = (
        ExcessAttachedBathroomPolicy.REMOVE
    )
    optional_room_failures: OptionalRoomFailurePolicy = (
        OptionalRoomFailurePolicy.REMOVE
    )
    derive_living_room: bool = True
    hallway_count: int = 2
    hallway_min_width: float = 10.0
    hallway_min_height: float = 10.0


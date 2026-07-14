from dataclasses import dataclass
from enum import Enum
from typing import NewType

# These types are currently not being actively used. There are in configuration phase to layer replace as the better data structure for the project flow.

RoomId = NewType("RoomId", str)


class RoomType(str, Enum):
    BEDROOM = "bedroom"
    BATHROOM = "bathroom"
    ATTACHED_BATHROOM = "attached_bathroom"
    LIVING_ROOM = "living_room"
    KITCHEN = "kitchen"
    DINING_ROOM = "dining_room"
    HALLWAY = "hallway"
    VERANDA = "veranda"
    GARAGE = "garage"
    OPEN_AREA = "open_area"


@dataclass(frozen=True)
class RoomSizeSpec:
    min_width: float
    max_width: float
    min_height: float
    max_height: float
    min_area: float
    max_area: float


@dataclass(frozen=True)
class RoomSpec:
    id: RoomId
    room_type: RoomType
    name: str
    size: RoomSizeSpec
    required: bool = True


@dataclass(frozen=True)
class FloorSpec:
    width: float
    height: float

class MatchPolicy(str, Enum):
    AND = "and"
    OR = "or"


class ConstraintStrength(str, Enum):
    HARD = "hard"
    SOFT = "soft"


@dataclass(frozen=True)
class RoomRelationSpec:
    source_room_id: RoomId
    target_room_ids: tuple[RoomId, ...]
    match_policy: MatchPolicy
    strength: ConstraintStrength


# Main Type for floor plan generation specification
@dataclass(frozen=True)
class FloorPlanGenerationSpec:
    floor: FloorSpec
    rooms: tuple[RoomSpec, ...]
    room_relations: tuple[RoomRelationSpec, ...]
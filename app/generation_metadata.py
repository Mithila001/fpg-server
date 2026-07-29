from __future__ import annotations

from dataclasses import dataclass

from app.algorithms.types_new import RoomType

METADATA_SCHEMA_VERSION = 1
FLOOR_AREA_BUFFER = 500.0
HALLWAY_AREA_BUFFER = 300.0
HALLWAY_COUNT = 1


@dataclass(frozen=True, slots=True)
class RoomRequirement:
    room_type: RoomType
    minimum: int
    maximum: int
    client_selectable: bool = True


@dataclass(frozen=True, slots=True)
class CompatibleAspectRatio:
    label: str
    value: float


ROOM_REQUIREMENTS: tuple[RoomRequirement, ...] = (
    RoomRequirement(RoomType.BEDROOM, 1, 4),
    RoomRequirement(RoomType.BATHROOM, 1, 4),
    RoomRequirement(RoomType.ATTACHED_BATHROOM, 0, 4),
    RoomRequirement(RoomType.LIVING_ROOM, 1, 1),
    RoomRequirement(RoomType.KITCHEN, 1, 1),
    RoomRequirement(RoomType.DINING_ROOM, 1, 1),
    RoomRequirement(RoomType.HALLWAY, 1, 1, client_selectable=False),
    RoomRequirement(RoomType.VERANDA, 1, 1),
    RoomRequirement(RoomType.GARAGE, 0, 1),
)

COMPATIBLE_ASPECT_RATIOS: tuple[CompatibleAspectRatio, ...] = (
    CompatibleAspectRatio("1:2", 0.5),
    CompatibleAspectRatio("3:4", 0.75),
    CompatibleAspectRatio("1:1", 1.0),
    CompatibleAspectRatio("4:3", 4.0 / 3.0),
    CompatibleAspectRatio("2:1", 2.0),
)

CLIENT_ROOM_REQUIREMENTS = tuple(
    requirement for requirement in ROOM_REQUIREMENTS if requirement.client_selectable
)
CLIENT_ROOM_TYPES = frozenset(
    requirement.room_type for requirement in CLIENT_ROOM_REQUIREMENTS
)


def canonical_aspect_ratio(value: float, *, tolerance: float = 1e-6) -> float | None:
    for supported in COMPATIBLE_ASPECT_RATIOS:
        if abs(value - supported.value) <= tolerance:
            return supported.value
    return None

"""Utilities for injecting extender rooms into the solver pipeline."""

from __future__ import annotations

from typing import Any

from app.algorithms.types import RoomData
from app.algorithms.fpg_rooms.utils.extender_config import LIVING_ROOM_EXTENDER_CONFIGS


def build_extender_room_data() -> list[RoomData]:
    """Build RoomData objects for all configured extender rooms.

    Returns a list of RoomData with is_extender=True and parent_room_name set.

    Returns:
        List of RoomData for extender rooms (e.g., living_room_ext).
    """
    extender_rooms: list[RoomData] = []

    for extender_config in LIVING_ROOM_EXTENDER_CONFIGS:
        room_data = RoomData(
            name=extender_config.name,
            type=extender_config.parent_room_name,  # Use parent type for compatibility
            min_w=extender_config.min_w,
            min_h=extender_config.min_h,
            max_w=extender_config.max_w,
            max_h=extender_config.max_h,
            is_extender=True,
            parent_room_name=extender_config.parent_room_name,
        )
        extender_rooms.append(room_data)

    return extender_rooms


def inject_extenders_into_requirements(
    requirements: type,
) -> type:
    """Inject extender room definitions into FpgRequirements.

    Modifies the requirements object to include extender rooms in the room list.

    Args:
        requirements: FpgRequirements object to be modified.

    Returns:
        The modified FpgRequirements object with extender rooms added.
    """
    extender_rooms = build_extender_room_data()

    # Add only missing extenders to keep this function idempotent.
    existing_names = {room.name for room in requirements.rooms}
    missing_extenders = [
        room for room in extender_rooms if room.name not in existing_names
    ]
    requirements.rooms.extend(missing_extenders)

    return requirements


def filter_extenders_from_solution(
    solution_rooms: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Separate extender rooms from regular rooms in the solution.

    Args:
        solution_rooms: List of room dicts from solver solution.

    Returns:
        Tuple of (regular_rooms, extender_rooms).
    """
    regular_rooms: list[dict[str, Any]] = []
    extender_rooms: list[dict[str, Any]] = []

    for room in solution_rooms:
        room_name = str(room.get("name", ""))
        if room_name.endswith("_ext"):
            extender_rooms.append(room)
        else:
            regular_rooms.append(room)

    return regular_rooms, extender_rooms

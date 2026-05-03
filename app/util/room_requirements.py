import math
from typing import List, Sequence

from app.algorithms.types import RoomData
from app.types.room_size_constraint import RoomSizeConstraint


def floor_values(value: float) -> int:
    """Convert float value to integer by flooring (rounding down).

    Args:
        value: Float value to floor

    Returns:
        Floored integer value (e.g., 5.5 -> 5, 5.3 -> 5, 4.9 -> 4)
    """
    return int(math.floor(value))


def normalize_db_data_requirements(
    rooms: List[RoomData],
    constraints: Sequence[RoomSizeConstraint],
) -> List[RoomData]:
    """Normalize room dimensions from DB constraints with strict validation.

    For each room type, use the DB value when present. If any required dimension
    is missing, raise an error (no defaults allowed).

    Args:
        rooms: List of room instances from template
        constraints: Room size constraints from database

    Returns:
        Normalized rooms with dimensions from constraints

    Raises:
        ValueError: If constraint not found or missing dimensions
    """
    constraints_by_type_size: dict[str, dict[str, RoomSizeConstraint]] = {}
    for constraint in constraints:
        room_type = str(constraint.type or "").strip()
        size = str(constraint.size or "").strip()
        if not room_type or not size:
            continue
        if room_type not in constraints_by_type_size:
            constraints_by_type_size[room_type] = {}
        constraints_by_type_size[room_type][size] = constraint

    def get_constraint_for(room_type: str, room_size: str) -> RoomSizeConstraint:
        size_map = constraints_by_type_size.get(room_type)
        if not size_map:
            raise ValueError(
                f"ERROR: Room type '{room_type}' has no constraint presets in database"
            )
        constraint = size_map.get(room_size)
        if not constraint:
            available_sizes = ", ".join(sorted(size_map.keys()))
            raise ValueError(
                f"ERROR: Room type '{room_type}' does not support size '{room_size}'. "
                f"Available sizes: {available_sizes}"
            )
        return constraint

    normalized: List[RoomData] = []

    for room in rooms:
        if room.type == "livingRoom":
            raise ValueError("ERROR: livingRoom must not be provided by the template")

        room_size = str(room.size or "").strip()
        if not room_size:
            raise ValueError(
                f"ERROR: Room '{room.name}' of type '{room.type}' is missing required 'size'"
            )

        constraint = get_constraint_for(room.type, room_size)

        # Strict validation: all dimensions must be present, no defaults
        if constraint.min_w is None:
            raise ValueError(
                f"ERROR: Room type '{room.type}' missing min_w constraint in database"
            )
        if constraint.min_h is None:
            raise ValueError(
                f"ERROR: Room type '{room.type}' missing min_h constraint in database"
            )
        if constraint.max_w is None:
            raise ValueError(
                f"ERROR: Room type '{room.type}' missing max_w constraint in database"
            )
        if constraint.max_h is None:
            raise ValueError(
                f"ERROR: Room type '{room.type}' missing max_h constraint in database"
            )

        min_w = int(constraint.min_w)
        min_h = int(constraint.min_h)
        max_w = int(constraint.max_w)
        max_h = int(constraint.max_h)

        # Validate dimension ranges
        if min_w <= 0 or min_h <= 0 or max_w <= 0 or max_h <= 0:
            raise ValueError(
                f"ERROR: Room type '{room.type}' has non-positive dimensions: "
                f"min_w={min_w}, min_h={min_h}, max_w={max_w}, max_h={max_h}"
            )

        if min_w > max_w or min_h > max_h:
            raise ValueError(
                f"ERROR: Room type '{room.type}' has invalid dimension ranges: "
                f"min_w={min_w} > max_w={max_w} or min_h={min_h} > max_h={max_h}"
            )

        normalized.append(
            RoomData(
                name=room.name,
                type=room.type,
                min_w=min_w,
                min_h=min_h,
                max_w=max_w,
                max_h=max_h,
                size=room_size,
            )
        )

    living_room_size_map = constraints_by_type_size.get("livingRoom")
    if not living_room_size_map:
        raise ValueError("ERROR: livingRoom has no constraint presets in database")

    living_room_size = (
        "regular"
        if "regular" in living_room_size_map
        else next(iter(living_room_size_map))
    )
    living_room_constraint = get_constraint_for("livingRoom", living_room_size)

    if living_room_constraint.min_w is None:
        raise ValueError("ERROR: livingRoom missing min_w constraint in database")
    if living_room_constraint.min_h is None:
        raise ValueError("ERROR: livingRoom missing min_h constraint in database")
    if living_room_constraint.max_w is None:
        raise ValueError("ERROR: livingRoom missing max_w constraint in database")
    if living_room_constraint.max_h is None:
        raise ValueError("ERROR: livingRoom missing max_h constraint in database")

    living_min_w = int(living_room_constraint.min_w)
    living_min_h = int(living_room_constraint.min_h)
    living_max_w = int(living_room_constraint.max_w)
    living_max_h = int(living_room_constraint.max_h)

    if living_min_w <= 0 or living_min_h <= 0 or living_max_w <= 0 or living_max_h <= 0:
        raise ValueError(
            "ERROR: livingRoom has non-positive dimensions: "
            f"min_w={living_min_w}, min_h={living_min_h}, max_w={living_max_w}, max_h={living_max_h}"
        )

    if living_min_w > living_max_w or living_min_h > living_max_h:
        raise ValueError(
            "ERROR: livingRoom has invalid dimension ranges: "
            f"min_w={living_min_w} > max_w={living_max_w} or min_h={living_min_h} > max_h={living_max_h}"
        )

    normalized.append(
        RoomData(
            name="livingRoom1",
            type="livingRoom",
            min_w=living_min_w,
            min_h=living_min_h,
            max_w=living_max_w,
            max_h=living_max_h,
            size=living_room_size,
        )
    )

    return normalized

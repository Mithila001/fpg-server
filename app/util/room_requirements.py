from typing import List, Sequence

from app.algorithms.floor_plan_generator.types.room import RoomData
from app.models.room_size_constraint import RoomSizeConstraint


def normalize_requirements(
    rooms: List[RoomData],
    constraints: Sequence[RoomSizeConstraint],
) -> List[RoomData]:
    """Normalize room dimensions from DB constraints with simple defaults.

    For each room type, use the DB value when present; otherwise use 10.
    """
    constraints_by_type = {c.type: c for c in constraints}
    normalized: List[RoomData] = []

    for room in rooms:
        constraint = constraints_by_type.get(room.type)

        if not constraint:
            raise ValueError(
                f"ERROR: Room type '{room.type}' has no constraint record in database"
            )

        min_w = int(constraint.min_w) if constraint.min_w is not None else 10
        min_h = int(constraint.min_h) if constraint.min_h is not None else 10
        max_w = int(constraint.max_w) if constraint.max_w is not None else 1000
        max_h = int(constraint.max_h) if constraint.max_h is not None else 1000

        normalized.append(
            RoomData(
                name=room.name,
                type=room.type,
                min_w=min_w,
                min_h=min_h,
                max_w=max_w,
                max_h=max_h,
            )
        )

    return normalized

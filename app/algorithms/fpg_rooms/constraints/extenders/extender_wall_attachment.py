"""Hard constraint for extender room wall attachment to parent room.

Ensures that each extender room:
1. Is adjacent to its parent room on exactly one side (N/S/E/W)
2. Has its wall segment fully contained within the parent's corresponding wall segment
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ortools.sat.python import cp_model

if TYPE_CHECKING:
    from app.algorithms.fpg_rooms.solver_models.room import Room


def add_extender_wall_attachment_constraint(
    model: Any,
    rooms: list[Room],
) -> None:
    """Add hard constraint: extender rooms must attach to parent room via one wall.

    For each extender room, ensures:
    - It is placed adjacent to parent on exactly one side (north/south/east/west)
    - Its wall segment is fully contained within parent's corresponding wall

    Args:
        model: CP-SAT solver model.
        rooms: List of all rooms (includes parent and extender rooms).
    """
    # Build a map of room names to Room objects for quick lookup
    room_map = {room.name: room for room in rooms}

    # Find all extender rooms and their parents
    for room in rooms:
        # Use the explicit flag instead of checking the name string
        if not room.is_extender or not room.parent_room_name:
            continue

        # Look up the parent using the explicit parent name from RoomData
        parent = room_map.get(room.parent_room_name)
        if parent:
            add_single_extender_wall_constraint(model, parent, room)


def is_extender_room(room: Room) -> bool:
    """Check if a room is an extender room.

    Currently uses naming convention: extender rooms end with "_ext".

    Args:
        room: Room object to check.

    Returns:
        True if room is an extender, False otherwise.
    """
    return room.name.endswith("_ext")


def extract_parent_name(extender_name: str) -> str:
    """Extract parent room name from extender room name.

    Assumes extender names follow pattern: "{parent_name}_ext"

    Args:
        extender_name: Name of extender room (e.g., "living_room_ext").

    Returns:
        Parent room name (e.g., "living_room").
    """
    if extender_name.endswith("_ext"):
        return extender_name[:-4]  # Remove "_ext" suffix
    return extender_name


def add_single_extender_wall_constraint(
    model: Any,
    parent: Room,
    extender: Room,
) -> None:
    """Add constraint for a single extender-parent pair.

    Constraint: Extender attaches to parent on exactly one side, with wall segment
    fully contained within parent's corresponding wall.

    Args:
        model: CP-SAT solver model.
        parent: Parent room.
        extender: Extender room.
    """
    assert parent.x is not None
    assert parent.y is not None
    assert parent.x_end is not None
    assert parent.y_end is not None
    assert extender.x is not None
    assert extender.y is not None
    assert extender.x_end is not None
    assert extender.y_end is not None

    # Create boolean variables for each side choice
    south_side = model.NewBoolVar(f"{extender.name}_on_south")
    north_side = model.NewBoolVar(f"{extender.name}_on_north")
    east_side = model.NewBoolVar(f"{extender.name}_on_east")
    west_side = model.NewBoolVar(f"{extender.name}_on_west")

    # Exactly one side must be chosen
    model.Add(south_side + north_side + east_side + west_side == 1)

    # South side: extender below parent
    # Adjacency: extender.y_end == parent.y
    # Wall containment: parent.x <= extender.x AND extender.x_end <= parent.x_end
    model.Add(extender.y_end == parent.y).OnlyEnforceIf(south_side)
    model.Add(parent.x <= extender.x).OnlyEnforceIf(south_side)
    model.Add(extender.x_end <= parent.x_end).OnlyEnforceIf(south_side)

    # North side: extender above parent
    # Adjacency: extender.y == parent.y_end
    # Wall containment: parent.x <= extender.x AND extender.x_end <= parent.x_end
    model.Add(extender.y == parent.y_end).OnlyEnforceIf(north_side)
    model.Add(parent.x <= extender.x).OnlyEnforceIf(north_side)
    model.Add(extender.x_end <= parent.x_end).OnlyEnforceIf(north_side)

    # East side: extender to the right of parent
    # Adjacency: extender.x == parent.x_end
    # Wall containment: parent.y <= extender.y AND extender.y_end <= parent.y_end
    model.Add(extender.x == parent.x_end).OnlyEnforceIf(east_side)
    model.Add(parent.y <= extender.y).OnlyEnforceIf(east_side)
    model.Add(extender.y_end <= parent.y_end).OnlyEnforceIf(east_side)

    # West side: extender to the left of parent
    # Adjacency: extender.x_end == parent.x
    # Wall containment: parent.y <= extender.y AND extender.y_end <= parent.y_end
    model.Add(extender.x_end == parent.x).OnlyEnforceIf(west_side)
    model.Add(parent.y <= extender.y).OnlyEnforceIf(west_side)
    model.Add(extender.y_end <= parent.y_end).OnlyEnforceIf(west_side)

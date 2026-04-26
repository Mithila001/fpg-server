"""Hard constraint for extender room wall attachment to parent room.

Ensures that each extender room:
1. Finds parent candidate(s) by room type.
2. If multiple candidates exist, attaches to exactly ONE of them.
3. Is adjacent to its chosen parent room on exactly one side (N/S/E/W).
4. Has its wall segment fully contained within the chosen parent's corresponding wall segment.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ortools.sat.python import cp_model

from app.dev.dev_print import debug_log_data

if TYPE_CHECKING:
    from app.algorithms.fpg_rooms.solver_models.room import Room


def add_extender_wall_attachment_constraint(
    model: Any,
    rooms: list[Room],
) -> None:
    """Add hard constraint: extender rooms must attach to a parent room via one wall.

    Looks up potential parent rooms by matching the extender's `parent_room_name`
    to the target room's `type`. If multiple candidates are found, the model ensures
    the constraint is satisfied for exactly ONE of them.

    Args:
        model: CP-SAT solver model.
        rooms: List of all rooms (includes parent and extender rooms).
    """

    # Build a map grouping non-extender rooms by their TYPE
    rooms_by_type: dict[str, list[Room]] = {}
    for room in rooms:
        if not room.is_extender:
            rooms_by_type.setdefault(room.type, []).append(room)

    print("\n\n Current Rooms:")
    for room in rooms:
        print(
            f"- {room.name} (type={room.type}, is_extender={room.is_extender}, parent_target={room.parent_room_name})"
        )

    # Find all extender rooms and attach them to a candidate parent
    for room in rooms:
        if not room.is_extender or not room.parent_room_name:
            continue

        target_type = room.parent_room_name
        candidates = rooms_by_type.get(target_type, [])

        if not candidates:
            debug_log_data(
                f"WARNING - No parent rooms of type '{target_type}' found for extender '{room.name}'",
                tag="EXTENDER_WALL_ATTACHMENT",
            )
            continue

        if len(candidates) == 1:
            # Only one candidate exists, apply constraint unconditionally
            debug_log_data(
                f"Attaching extender '{room.name}' to single parent '{candidates[0].name}'",
                tag="EXTENDER_WALL_ATTACHMENT",
            )
            add_single_extender_wall_constraint(model, candidates[0], room)
        else:
            # Multiple candidates exist, extender must choose exactly ONE
            debug_log_data(
                f"Extender '{room.name}' has {len(candidates)} candidate parents of type '{target_type}'",
                tag="EXTENDER_WALL_ATTACHMENT",
            )

            choice_vars = []
            for candidate in candidates:
                # Boolean var: True if THIS specific candidate is chosen as the parent
                is_chosen = model.NewBoolVar(
                    f"{room.name}_attaches_to_{candidate.name}"
                )
                choice_vars.append(is_chosen)

                # Apply the wall constraints conditionally based on is_chosen
                add_single_extender_wall_constraint(
                    model, candidate, room, is_active_var=is_chosen
                )

            # Constraint: Exactly one candidate must be chosen as the parent
            model.AddExactlyOne(choice_vars)


def add_single_extender_wall_constraint(
    model: Any,
    parent: Room,
    extender: Room,
    is_active_var: Any = None,
) -> None:
    """Add constraint for a single extender-parent pair.

    Constraint: Extender attaches to parent on exactly one side, with wall segment
    fully contained within parent's corresponding wall.

    Args:
        model: CP-SAT solver model.
        parent: Parent room.
        extender: Extender room.
        is_active_var: Optional boolean variable. If provided, these constraints
                       are only enforced if is_active_var is True.
    """
    assert parent.x is not None
    assert parent.y is not None
    assert parent.x_end is not None
    assert parent.y_end is not None
    assert extender.x is not None
    assert extender.y is not None
    assert extender.x_end is not None
    assert extender.y_end is not None

    # Prefix ensures variables are unique even if the same extender is checked against multiple parents
    prefix = f"{extender.name}_to_{parent.name}"

    # Create boolean variables for each side choice
    south_side = model.NewBoolVar(f"{prefix}_on_south")
    north_side = model.NewBoolVar(f"{prefix}_on_north")
    east_side = model.NewBoolVar(f"{prefix}_on_east")
    west_side = model.NewBoolVar(f"{prefix}_on_west")

    sides = [south_side, north_side, east_side, west_side]

    if is_active_var is not None:
        # If this parent IS chosen, exactly one side must be true
        model.Add(sum(sides) == 1).OnlyEnforceIf(is_active_var)
        # If this parent IS NOT chosen, all sides must be false (disables adjacency checks below)
        model.Add(sum(sides) == 0).OnlyEnforceIf(is_active_var.Not())
    else:
        # Exactly one side must be chosen unconditionally
        model.Add(sum(sides) == 1)

    # South side: extender below parent
    model.Add(extender.y_end == parent.y).OnlyEnforceIf(south_side)
    model.Add(parent.x <= extender.x).OnlyEnforceIf(south_side)
    model.Add(extender.x_end <= parent.x_end).OnlyEnforceIf(south_side)

    # North side: extender above parent
    model.Add(extender.y == parent.y_end).OnlyEnforceIf(north_side)
    model.Add(parent.x <= extender.x).OnlyEnforceIf(north_side)
    model.Add(extender.x_end <= parent.x_end).OnlyEnforceIf(north_side)

    # East side: extender to the right of parent
    model.Add(extender.x == parent.x_end).OnlyEnforceIf(east_side)
    model.Add(parent.y <= extender.y).OnlyEnforceIf(east_side)
    model.Add(extender.y_end <= parent.y_end).OnlyEnforceIf(east_side)

    # West side: extender to the left of parent
    model.Add(extender.x_end == parent.x).OnlyEnforceIf(west_side)
    model.Add(parent.y <= extender.y).OnlyEnforceIf(west_side)
    model.Add(extender.y_end <= parent.y_end).OnlyEnforceIf(west_side)

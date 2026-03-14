from ortools.sat.python import cp_model
from typing import List, Dict, Any

from ..solver_models.room import Room
from app.schemas.db.room_relations_constraints import RoomRelationsConstraintBase


# hard constraint logic is now handled by `_conditional_constraint` with
# a constant ``True`` enforcer; the old `_constraint` helper has been removed.


def _conditional_constraint(
    model: cp_model.CpModel,
    room1: Room,
    room2: Room,
    enforcer: Any | None = None,
) -> None:
    """Applies touch constraints between ``room1`` and ``room2``.

    When ``enforcer`` is ``None`` the constraints are always active (equiv-
    alent to the old ``_constraint``).  Otherwise, the boolean ``enforcer``
    determines whether the pair is required.  This lets a single helper cover
    both the "hard" and "selected" cases.
    """
    suffix = f"{room1.name}_{room2.name}"

    touch_right = model.NewBoolVar(f"touch_right_{suffix}")  # type: ignore
    touch_left = model.NewBoolVar(f"touch_left_{suffix}")  # type: ignore
    touch_top = model.NewBoolVar(f"touch_top_{suffix}")  # type: ignore
    touch_bottom = model.NewBoolVar(f"touch_bottom_{suffix}")  # type: ignore

    conds = []
    if enforcer is not None:
        conds.append(enforcer)

    model.Add(room1.x == room2.x_end).OnlyEnforceIf(conds + [touch_right])  # type: ignore
    model.Add(room1.x != room2.x_end).OnlyEnforceIf(conds + [touch_right.Not()])  # type: ignore

    model.Add(room1.x_end == room2.x).OnlyEnforceIf(conds + [touch_left])  # type: ignore
    model.Add(room1.x_end != room2.x).OnlyEnforceIf(conds + [touch_left.Not()])  # type: ignore

    model.Add(room1.y == room2.y_end).OnlyEnforceIf(conds + [touch_top])  # type: ignore
    model.Add(room1.y != room2.y_end).OnlyEnforceIf(conds + [touch_top.Not()])  # type: ignore

    model.Add(room1.y_end == room2.y).OnlyEnforceIf(conds + [touch_bottom])  # type: ignore
    model.Add(room1.y_end != room2.y).OnlyEnforceIf(conds + [touch_bottom.Not()])  # type: ignore

    # when the pair is active, one of the sides must touch
    if enforcer is not None:
        model.AddBoolOr(  # type: ignore
            [touch_right, touch_left, touch_top, touch_bottom]
        ).OnlyEnforceIf(enforcer)  # type: ignore
    else:
        model.AddBoolOr([touch_right, touch_left, touch_top, touch_bottom])  # type: ignore

    MIN_OVERLAP = 10
    model.Add(room1.y + MIN_OVERLAP < room2.y_end).OnlyEnforceIf(conds + [touch_right])  # type: ignore
    model.Add(room2.y + MIN_OVERLAP < room1.y_end).OnlyEnforceIf(conds + [touch_right])  # type: ignore
    model.Add(room1.x + MIN_OVERLAP < room2.x_end).OnlyEnforceIf(conds + [touch_top])  # type: ignore
    model.Add(room2.x + MIN_OVERLAP < room1.x_end).OnlyEnforceIf(conds + [touch_top])  # type: ignore


def adjacency_constraints(
    model: cp_model.CpModel,
    rooms_list: List[Room],
    relations: List[RoomRelationsConstraintBase],
) -> None:
    """Apply adjacency rules dynamically from database records."""
    # print("\nRoom Lists" + str(rooms_list))
    # print("\nRelations" + str(relations), "\n")
    for rec in relations:
        # 1. FIX Pylance Error: Ensure related_room is a list, not None
        related_types = rec.related_room or []
        if not related_types:
            continue

        # 2. FIX Bedroom 2: Find ALL rooms of this type (e.g., all Bedrooms)
        # Instead of 'next()', we use a list comprehension to get everyone.
        subject_rooms = [r for r in rooms_list if r.type == rec.room_type]
        if not subject_rooms:
            continue

        # 3. Find all potential candidate neighbors
        candidates = [r for r in rooms_list if r.type in related_types]
        if not candidates:
            continue

        # 4. Apply the rule to EACH subject room (Bedroom 1, Bedroom 2, etc.)
        for room1 in subject_rooms:
            if len(candidates) == 1:
                # If only one option (e.g., Living Room), it's a hard requirement
                _conditional_constraint(model, room1, candidates[0], enforcer=None)
            else:
                # If multiple options, create a master 'OR' for this specific room
                adj_switches = []
                for room2 in candidates:
                    # Don't let a room try to be adjacent to itself
                    if room1.name == room2.name:
                        continue

                    is_adj = model.NewBoolVar(f"is_adj_{room1.name}_{room2.name}")  # type: ignore
                    adj_switches.append(is_adj)
                    _conditional_constraint(model, room1, room2, enforcer=is_adj)

                if adj_switches:
                    model.AddBoolOr(adj_switches)  # type: ignore

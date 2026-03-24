from ortools.sat.python import cp_model
from typing import List

from ..solver_models.room import Room


def room_location_hard(
    model: cp_model.CpModel,
    rooms: List[Room],
) -> None:
    """Enforce living room as the bottom-most room by center y.

    Uses doubled-center arithmetic to stay in integers:
    center_y * 2 == room.y + room.y_end
    """
    living_rooms = [r for r in rooms if r.type == "livingRoom"]
    if not living_rooms:
        return

    living_room = living_rooms[0]

    for room in rooms:
        if room is living_room:
            continue
        model.Add(living_room.y + living_room.y_end >= room.y + room.y_end)  # type: ignore


def room_location_soft(
    model: cp_model.CpModel,
    rooms: List[Room],
    floor_height: float,
    bathroom_weight: int = 1,
) -> cp_model.LinearExprT:
    """Return soft cost encouraging bathrooms toward plus-y direction.

    Lower cost means larger bathroom center y.
    """
    if bathroom_weight <= 0:
        bathroom_weight = 1

    h_int = int(floor_height)
    max_center_y2 = h_int * 2

    terms: List[cp_model.LinearExprT] = []
    for room in rooms:
        if room.type != "bathroom":
            continue

        # penalty decreases as (room.y + room.y_end) increases
        penalty = max_center_y2 - (room.y + room.y_end)  # type: ignore
        terms.append(penalty * bathroom_weight)

    if not terms:
        return 0

    return cp_model.LinearExpr.Sum(terms)  # type: ignore
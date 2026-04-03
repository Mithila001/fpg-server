from typing import List

from ortools.sat.python import cp_model

from ...solver_models.room import Room


def add_living_room_bottom_most_constraint(
    model: cp_model.CpModel,
    rooms: List[Room],
) -> None:
    """Keep living room as the bottom-most room by center y."""
    living_rooms = [room for room in rooms if room.type == "livingRoom"]
    if not living_rooms:
        return

    living_room = living_rooms[0]

    for room in rooms:
        if room is living_room:
            continue
        model.Add(living_room.y + living_room.y_end >= room.y + room.y_end)  # type: ignore

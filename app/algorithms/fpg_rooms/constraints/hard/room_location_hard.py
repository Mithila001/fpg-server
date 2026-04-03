from typing import List

from ortools.sat.python import cp_model

from ...solver_models.room import Room


def add_living_room_bottom_most_constraint(
    model: cp_model.CpModel,
    rooms: List[Room],
) -> None:
    """Keep veranda (or livingRoom fallback) as the bottom-most room by center y."""
    veranda_rooms = [room for room in rooms if room.type == "veranda"]
    if veranda_rooms:
        bottom_room = veranda_rooms[0]
    else:
        living_rooms = [room for room in rooms if room.type == "livingRoom"]
        if not living_rooms:
            return
        bottom_room = living_rooms[0]

    for room in rooms:
        if room is bottom_room:
            continue
        model.Add(bottom_room.y + bottom_room.y_end >= room.y + room.y_end)  # type: ignore

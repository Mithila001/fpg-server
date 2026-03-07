from ortools.sat.python import cp_model
from typing import List
from ..models.room import Room
from ..utils.tracker import tracker


def add_room_size_hierarchy(model: cp_model.CpModel, rooms: List[Room]):
    """
    Enforce proportional area relationships between room types relative to
    the Living Room.
    """

    def get_room(room_type: str) -> Room | None:
        for r in rooms:
            if r.type == room_type:
                return r
        tracker.log_skip("Room Size Hierarchy", f"No Type:{room_type} found")
        return None

    living_room = get_room("LivingRoom")
    if not living_room:
        tracker.log_skip("Room Size Hierarchy", "No LivingRoom found")
        return

    hierarchy = {
        "Bedroom": (50, 70),
        "Kitchen": (40, 50),
        "Bathroom": (15, 30),
    }

    for room_type, (min_p, max_p) in hierarchy.items():
        target_rooms = [r for r in rooms if r.type == room_type]
        for target_room in target_rooms:
            model.Add(target_room.area * 100 >= living_room.area * min_p)  # type: ignore
            model.Add(target_room.area * 100 <= living_room.area * max_p)  # type: ignore

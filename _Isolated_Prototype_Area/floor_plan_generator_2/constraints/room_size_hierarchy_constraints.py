from ortools.sat.python import cp_model
from typing import List
from ..models.room import Room
from ..utils.tracker import tracker

def add_room_size_hierarchy(model: cp_model.CpModel, rooms: List[Room]):

    # Helper to find room by type
    def get_room(type: str) -> Room | None:
        for r in rooms:
            if r.type == type:
                return r
        tracker.log_skip("Room Size Hierarchy", f"No Type:{type} found")
        return None
    
    living_room = get_room("LivingRoom")
    if not living_room:
        tracker.log_skip("Room Size Hierarchy", "No LivingRoom found")
        return

    hierarchy = {
        "Bedroom": (50, 70),
        "Kitchen": (40, 50),
        "Bathroom": (15, 30)
    }

    for room_type, (min_p, max_p) in hierarchy.items():
        # Filter for all rooms of this type
        target_rooms = [r for r in rooms if r.type == room_type]
        for target_room in target_rooms:
            # Type ignore on math operations for OR-Tools vars
            model.Add(target_room.area * 100 >= living_room.area * min_p) # type: ignore
            model.Add(target_room.area * 100 <= living_room.area * max_p) # type: ignore

    print("Added room size hierarchy constraints")
from ortools.sat.python import cp_model
from typing import List
from ..models.room import Room

def add_room_size_hierarchy(model: cp_model.CpModel, rooms: List[Room]):
    def get_room(name: str) -> Room | None:
        return next((r for r in rooms if r.name == name), None)
    
    living_room = get_room("Living Room")
    if not living_room:
        return

    hierarchy = {
        "Bedroom": (40, 60),
        "Kitchen": (60, 80),
        "Bathroom": (15, 30)
    }

    for name, (min_p, max_p) in hierarchy.items():
        target_room = get_room(name)
        if target_room:
            # Type ignore on math operations for OR-Tools vars
            model.Add(target_room.area * 100 >= living_room.area * min_p) # type: ignore
            model.Add(target_room.area * 100 <= living_room.area * max_p) # type: ignore

    print("Added room size hierarchy constraints")
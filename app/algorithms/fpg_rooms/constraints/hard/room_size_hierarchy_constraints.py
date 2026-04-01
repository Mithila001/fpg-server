from typing import List

from ortools.sat.python import cp_model

from app.core.fpg_rooms.config_fpg import ROOM_SIZE_HIERARCHY

from ...solver_models.room import Room
from ...utils.tracker import tracker


def add_room_size_hierarchy(model: cp_model.CpModel, rooms: List[Room]) -> None:
    """Enforce proportional room areas relative to the living room."""

    def get_room(room_type: str) -> Room | None:
        for room in rooms:
            if room.type == room_type:
                return room
        tracker.log_skip("Room Size Hierarchy", f"No Type:{room_type} found")
        return None

    living_room = get_room("livingRoom")
    if not living_room:
        tracker.log_skip("Room Size Hierarchy", "No LivingRoom found")
        return

    for room_type, (min_pct, max_pct) in ROOM_SIZE_HIERARCHY.items():
        target_rooms = [room for room in rooms if room.type == room_type]
        for target_room in target_rooms:
            model.Add(target_room.area * 100 >= living_room.area * min_pct)  # type: ignore
            model.Add(target_room.area * 100 <= living_room.area * max_pct)  # type: ignore

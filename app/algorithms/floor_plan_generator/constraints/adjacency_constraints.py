from ortools.sat.python import cp_model
from typing import List, Optional, Dict, Any
from ..solver_models.room import Room


def add_adjacency_constraint(
    model: cp_model.CpModel, room1: Room, room2: Room
) -> Dict[str, Any]:
    """Ensures room1 and room2 are touching on one side."""
    touch_right = model.NewBoolVar(f"{room1.name}_is_right_of_{room2.name}")
    touch_left = model.NewBoolVar(f"{room1.name}_is_left_of_{room2.name}")
    touch_top = model.NewBoolVar(f"{room1.name}_is_above_{room2.name}")
    touch_bottom = model.NewBoolVar(f"{room1.name}_is_below_{room2.name}")

    model.Add(room1.x == room2.x_end).OnlyEnforceIf(touch_right)  # type: ignore
    model.Add(room1.x != room2.x_end).OnlyEnforceIf(touch_right.Not())  # type: ignore

    model.Add(room1.x_end == room2.x).OnlyEnforceIf(touch_left)  # type: ignore
    model.Add(room1.x_end != room2.x).OnlyEnforceIf(touch_left.Not())  # type: ignore

    model.Add(room1.y == room2.y_end).OnlyEnforceIf(touch_top)  # type: ignore
    model.Add(room1.y != room2.y_end).OnlyEnforceIf(touch_top.Not())  # type: ignore

    model.Add(room1.y_end == room2.y).OnlyEnforceIf(touch_bottom)  # type: ignore
    model.Add(room1.y_end != room2.y).OnlyEnforceIf(touch_bottom.Not())  # type: ignore

    model.AddBoolOr([touch_right, touch_left, touch_top, touch_bottom])

    MIN_WALL = 10
    model.Add(room1.y + MIN_WALL < room2.y_end).OnlyEnforceIf(touch_right)  # type: ignore
    model.Add(room2.y + MIN_WALL < room1.y_end).OnlyEnforceIf(touch_right)  # type: ignore
    model.Add(room1.x + MIN_WALL < room2.x_end).OnlyEnforceIf(touch_top)  # type: ignore
    model.Add(room2.x + MIN_WALL < room1.x_end).OnlyEnforceIf(touch_top)  # type: ignore

    return {
        "right": touch_right,
        "left": touch_left,
        "top": touch_top,
        "bottom": touch_bottom,
    }


def add_kitchen_living_adjacency(
    model: cp_model.CpModel, rooms_list: List[Room]
) -> Optional[Dict[str, Any]]:
    """Enforce adjacency between Kitchen and Living Room if both exist."""
    kitchen_room = None
    living_room = None

    for room in rooms_list:
        if room.name == "Kitchen":
            kitchen_room = room
        elif room.name == "Living Room":
            living_room = room

    if kitchen_room and living_room:
        return add_adjacency_constraint(model, kitchen_room, living_room)
    return None

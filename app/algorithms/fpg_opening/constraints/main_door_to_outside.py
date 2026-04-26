from __future__ import annotations

from ortools.sat.python import cp_model

from app.algorithms.types.solvers import MainDoorCpSatVariables, ScaledRoomBounds
from app.algorithms.types.solvers.cp_model_like import CpModelLike
from app.core.fpg_opening_config import CARDINAL_SIDES


_SIDES: tuple[str, ...] = CARDINAL_SIDES


def _priority_rank_map(side_priority: tuple[str, ...]) -> dict[str, int]:
    rank_map: dict[str, int] = {}
    for index, side in enumerate(side_priority):
        key = side.strip().lower()
        if key in _SIDES and key not in rank_map:
            rank_map[key] = index

    fallback_start = len(rank_map)
    for side in _SIDES:
        if side not in rank_map:
            rank_map[side] = fallback_start
            fallback_start += 1

    return rank_map


def add_main_door_to_outside_constraint(
    model: CpModelLike,
    room: ScaledRoomBounds,
    exterior_sides: set[str],
    side_priority: tuple[str, ...],
    preferred_door_length: int,
) -> tuple[MainDoorCpSatVariables, cp_model.LinearExprT]:
    """Add the main-door-to-outside requirement to a per-room CP-SAT model.

    The model chooses exactly one valid exterior side and places a centered door
    segment on that side.
    """
    room_x = room["x"]
    room_y = room["y"]
    room_x_end = room["x_end"]
    room_y_end = room["y_end"]

    if not exterior_sides:
        raise ValueError("exterior_sides cannot be empty")

    x1 = model.NewIntVar(room_x, room_x_end, "door_x1")
    y1 = model.NewIntVar(room_y, room_y_end, "door_y1")
    x2 = model.NewIntVar(room_x, room_x_end, "door_x2")
    y2 = model.NewIntVar(room_y, room_y_end, "door_y2")

    side_selected = {side: model.NewBoolVar(f"select_{side}") for side in _SIDES}

    exterior_normalized = {side.strip().lower() for side in exterior_sides}
    for side in _SIDES:
        if side not in exterior_normalized:
            model.Add(side_selected[side] == 0)

    model.Add(sum(side_selected.values()) == 1)

    wall_width = room_x_end - room_x
    wall_height = room_y_end - room_y
    horizontal_door_length = max(1, min(preferred_door_length, wall_width))
    vertical_door_length = max(1, min(preferred_door_length, wall_height))

    for side in _SIDES:
        selected = side_selected[side]
        if side == "south":
            x1_const = room_x + ((wall_width - horizontal_door_length) // 2)
            x2_const = x1_const + horizontal_door_length
            model.Add(x1 == x1_const).OnlyEnforceIf(selected)
            model.Add(x2 == x2_const).OnlyEnforceIf(selected)
            model.Add(y1 == room_y).OnlyEnforceIf(selected)
            model.Add(y2 == room_y).OnlyEnforceIf(selected)

        elif side == "north":
            x1_const = room_x + ((wall_width - horizontal_door_length) // 2)
            x2_const = x1_const + horizontal_door_length
            model.Add(x1 == x1_const).OnlyEnforceIf(selected)
            model.Add(x2 == x2_const).OnlyEnforceIf(selected)
            model.Add(y1 == room_y_end).OnlyEnforceIf(selected)
            model.Add(y2 == room_y_end).OnlyEnforceIf(selected)

        elif side == "west":
            y1_const = room_y + ((wall_height - vertical_door_length) // 2)
            y2_const = y1_const + vertical_door_length
            model.Add(x1 == room_x).OnlyEnforceIf(selected)
            model.Add(x2 == room_x).OnlyEnforceIf(selected)
            model.Add(y1 == y1_const).OnlyEnforceIf(selected)
            model.Add(y2 == y2_const).OnlyEnforceIf(selected)

        else:  # east
            y1_const = room_y + ((wall_height - vertical_door_length) // 2)
            y2_const = y1_const + vertical_door_length
            model.Add(x1 == room_x_end).OnlyEnforceIf(selected)
            model.Add(x2 == room_x_end).OnlyEnforceIf(selected)
            model.Add(y1 == y1_const).OnlyEnforceIf(selected)
            model.Add(y2 == y2_const).OnlyEnforceIf(selected)

    rank_map = _priority_rank_map(side_priority)
    priority_terms = [rank_map[side] * side_selected[side] for side in _SIDES]
    priority_cost = cp_model.LinearExpr.Sum(priority_terms)

    return {
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
        "side_selected": side_selected,
    }, priority_cost

from __future__ import annotations

from typing import Dict, List

from ortools.sat.python import cp_model

from ...solver_models.room import Room


def _touch_constraints(
    model: cp_model.CpModel,
    room1: Room,
    room2: Room,
) -> Dict[str, cp_model.IntVar]:
    suffix = f"oa_{room1.name}_{room2.name}"

    touch_right = model.NewBoolVar(f"{suffix}_right")  # type: ignore
    touch_left = model.NewBoolVar(f"{suffix}_left")  # type: ignore
    touch_top = model.NewBoolVar(f"{suffix}_top")  # type: ignore
    touch_bottom = model.NewBoolVar(f"{suffix}_bottom")  # type: ignore

    model.Add(room1.x == room2.x_end).OnlyEnforceIf(touch_right)  # type: ignore
    model.Add(room1.x != room2.x_end).OnlyEnforceIf(touch_right.Not())  # type: ignore

    model.Add(room1.x_end == room2.x).OnlyEnforceIf(touch_left)  # type: ignore
    model.Add(room1.x_end != room2.x).OnlyEnforceIf(touch_left.Not())  # type: ignore

    model.Add(room1.y == room2.y_end).OnlyEnforceIf(touch_top)  # type: ignore
    model.Add(room1.y != room2.y_end).OnlyEnforceIf(touch_top.Not())  # type: ignore

    model.Add(room1.y_end == room2.y).OnlyEnforceIf(touch_bottom)  # type: ignore
    model.Add(room1.y_end != room2.y).OnlyEnforceIf(touch_bottom.Not())  # type: ignore

    return {
        "right": touch_right,
        "left": touch_left,
        "top": touch_top,
        "bottom": touch_bottom,
    }


def _build_side_touch_flag(
    model: cp_model.CpModel,
    touches: List[cp_model.IntVar],
    name: str,
) -> cp_model.IntVar:
    side_has_touch = model.NewBoolVar(name)  # type: ignore
    if not touches:
        model.Add(side_has_touch == 0)
        return side_has_touch

    total_touches = cp_model.LinearExpr.Sum(touches)
    model.Add(total_touches >= 1).OnlyEnforceIf(side_has_touch)
    model.Add(total_touches == 0).OnlyEnforceIf(side_has_touch.Not())
    return side_has_touch


def add_open_area_placement_constraints(
    model: cp_model.CpModel,
    rooms: List[Room],
) -> None:
    """Keep veranda front open (bottom) and at least one lateral side open."""
    target_rooms = [room for room in rooms if room.type == "veranda"]
    if not target_rooms:
        return

    for target in target_rooms:
        assert target.x is not None and target.y is not None
        assert target.x_end is not None and target.y_end is not None

        side_touches: Dict[str, List[cp_model.IntVar]] = {
            "right": [],
            "left": [],
            "top": [],
            "bottom": [],
        }

        for other in rooms:
            if other.name == target.name:
                continue

            assert other.x is not None and other.y is not None
            assert other.x_end is not None and other.y_end is not None

            touches = _touch_constraints(model, target, other)
            for side in side_touches:
                side_touches[side].append(touches[side])

        side_has_touch = {
            side: _build_side_touch_flag(model, touches, f"oa_side_touch_{target.name}_{side}")
            for side, touches in side_touches.items()
        }

        # Front side is bottom in this coordinate system and must remain exterior.
        model.Add(side_has_touch["bottom"] == 0)
        # At least one side adjacent to the front (left/right) must remain exterior.
        model.AddBoolOr([side_has_touch["left"].Not(), side_has_touch["right"].Not()])

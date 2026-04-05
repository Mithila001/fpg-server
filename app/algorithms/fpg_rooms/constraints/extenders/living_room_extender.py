from __future__ import annotations

from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from ...solver_models.room import Room


@dataclass(slots=True)
class ExtenderSolveContext:
    activation_vars: dict[str, cp_model.BoolVar] = field(default_factory=dict)
    objective_terms: list[cp_model.LinearExprT] = field(default_factory=list)


def _axis_overlap_length(
    model: cp_model.CpModel,
    start1: cp_model.IntVar,
    end1: cp_model.IntVar,
    start2: cp_model.IntVar,
    end2: cp_model.IntVar,
    suffix: str,
    coord_ub: int,
) -> cp_model.IntVar:
    overlap_start = model.NewIntVar(0, coord_ub, f"ext_ov_start_{suffix}")  # type: ignore
    overlap_end = model.NewIntVar(0, coord_ub, f"ext_ov_end_{suffix}")  # type: ignore
    model.AddMaxEquality(overlap_start, [start1, start2])
    model.AddMinEquality(overlap_end, [end1, end2])

    overlap_raw = model.NewIntVar(-coord_ub, coord_ub, f"ext_ov_raw_{suffix}")  # type: ignore
    model.Add(overlap_raw == overlap_end - overlap_start)

    overlap_len = model.NewIntVar(0, coord_ub, f"ext_ov_len_{suffix}")  # type: ignore
    model.AddMaxEquality(overlap_len, [overlap_raw, 0])
    return overlap_len


def add_living_room_extender_constraints(
    model: cp_model.CpModel,
    rooms: list[Room],
    *,
    active_min_size: int,
    perpendicular_max_size: int,
    inactive_size_cap: int,
    activation_penalty: int,
) -> ExtenderSolveContext:
    context = ExtenderSolveContext()

    living_room = next((r for r in rooms if r.type == "livingRoom"), None)
    if living_room is None:
        return context

    extenders = [r for r in rooms if r.type == "livingRoomExtender"]
    if not extenders:
        return context

    coord_ub = max(1, sum(max(room.max_w, room.max_h) for room in rooms))
    active_min = max(1, int(active_min_size))
    perpendicular_cap = max(active_min, int(perpendicular_max_size))
    inactive_cap = max(0, int(inactive_size_cap))
    penalty = max(0, int(activation_penalty))

    for extender in extenders:
        is_active = model.NewBoolVar(f"ext_active_{extender.name}")  # type: ignore
        context.activation_vars[extender.name] = is_active

        if penalty > 0:
            context.objective_terms.append(is_active * penalty)

        model.Add(extender.w >= active_min).OnlyEnforceIf(is_active)
        model.Add(extender.h >= active_min).OnlyEnforceIf(is_active)

        model.Add(extender.w <= inactive_cap).OnlyEnforceIf(is_active.Not())
        model.Add(extender.h <= inactive_cap).OnlyEnforceIf(is_active.Not())

        touch_right = model.NewBoolVar(f"ext_touch_right_{extender.name}")  # type: ignore
        touch_left = model.NewBoolVar(f"ext_touch_left_{extender.name}")  # type: ignore
        touch_top = model.NewBoolVar(f"ext_touch_top_{extender.name}")  # type: ignore
        touch_bottom = model.NewBoolVar(f"ext_touch_bottom_{extender.name}")  # type: ignore

        side_touches = [touch_right, touch_left, touch_top, touch_bottom]
        for side_touch in side_touches:
            model.AddImplication(side_touch, is_active)

        model.AddBoolOr(side_touches).OnlyEnforceIf(is_active)
        model.Add(sum(side_touches) == 1).OnlyEnforceIf(is_active)

        vertical_overlap = _axis_overlap_length(
            model,
            extender.y,
            extender.y_end,
            living_room.y,
            living_room.y_end,
            f"v_{extender.name}_{living_room.name}",
            coord_ub,
        )
        horizontal_overlap = _axis_overlap_length(
            model,
            extender.x,
            extender.x_end,
            living_room.x,
            living_room.x_end,
            f"h_{extender.name}_{living_room.name}",
            coord_ub,
        )

        model.Add(extender.x == living_room.x_end).OnlyEnforceIf(touch_right)
        model.Add(extender.x_end == living_room.x).OnlyEnforceIf(touch_left)
        model.Add(extender.y == living_room.y_end).OnlyEnforceIf(touch_top)
        model.Add(extender.y_end == living_room.y).OnlyEnforceIf(touch_bottom)

        model.Add(vertical_overlap == extender.h).OnlyEnforceIf(touch_right)
        model.Add(vertical_overlap == extender.h).OnlyEnforceIf(touch_left)
        model.Add(horizontal_overlap == extender.w).OnlyEnforceIf(touch_top)
        model.Add(horizontal_overlap == extender.w).OnlyEnforceIf(touch_bottom)

        model.Add(extender.w <= perpendicular_cap).OnlyEnforceIf(touch_right)
        model.Add(extender.w <= perpendicular_cap).OnlyEnforceIf(touch_left)
        model.Add(extender.h <= perpendicular_cap).OnlyEnforceIf(touch_top)
        model.Add(extender.h <= perpendicular_cap).OnlyEnforceIf(touch_bottom)

    return context

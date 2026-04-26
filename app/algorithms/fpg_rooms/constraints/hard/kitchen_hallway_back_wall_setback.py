"""Hard constraint for kitchen/hallway back-wall door setback.

At least one eligible back wall must preserve a clear zone directly behind it:
- If both kitchen and hallway exist: any one kitchen/hallway can satisfy it.
- If only one type exists: that type must satisfy it.
- If neither exists: no-op.

Coordinate reference:
- Back side is the top side (higher y), i.e., room.y_end.
"""

from __future__ import annotations

from typing import Any

from ortools.sat.python import cp_model

from app.core.fpg_rooms.config_fpg import (
    KITCHEN_HALLWAY_BACK_WALL_SETBACK_MAX_GAP,
    KITCHEN_HALLWAY_BACK_WALL_SETBACK_MIN_GAP,
)
from ...solver_models.room import Room


def _axis_overlap_bool(
    model: Any,
    a_start: cp_model.IntVar,
    a_end: cp_model.IntVar,
    b_start: cp_model.IntVar,
    b_end: cp_model.IntVar,
    name: str,
) -> cp_model.IntVar:
    overlap = model.NewBoolVar(name)

    a_before_b = model.NewBoolVar(f"{name}_a_before_b")
    b_before_a = model.NewBoolVar(f"{name}_b_before_a")

    model.Add(a_end <= b_start).OnlyEnforceIf(a_before_b)
    model.Add(a_end >= b_start + 1).OnlyEnforceIf(a_before_b.Not())

    model.Add(b_end <= a_start).OnlyEnforceIf(b_before_a)
    model.Add(b_end >= a_start + 1).OnlyEnforceIf(b_before_a.Not())

    model.AddBoolOr([a_before_b, b_before_a]).OnlyEnforceIf(overlap.Not())
    model.Add(a_before_b == 0).OnlyEnforceIf(overlap)
    model.Add(b_before_a == 0).OnlyEnforceIf(overlap)
    return overlap


def _ordered_bool(
    model: Any,
    lhs: cp_model.IntVar,
    rhs: Any,
    strict_less_name: str,
) -> cp_model.IntVar:
    lhs_less_rhs = model.NewBoolVar(strict_less_name)
    model.Add(lhs <= rhs - 1).OnlyEnforceIf(lhs_less_rhs)
    model.Add(lhs >= rhs).OnlyEnforceIf(lhs_less_rhs.Not())
    return lhs_less_rhs


def _and_of_literals(
    model: Any,
    left: cp_model.IntVar,
    right: cp_model.IntVar,
    name: str,
) -> cp_model.IntVar:
    out = model.NewBoolVar(name)
    model.AddBoolAnd([left, right]).OnlyEnforceIf(out)
    model.AddBoolOr([left.Not(), right.Not()]).OnlyEnforceIf(out.Not())
    return out


def _or_of_literals(
    model: Any,
    literals: list[cp_model.IntVar],
    name: str,
) -> cp_model.IntVar:
    if not literals:
        out = model.NewBoolVar(name)
        model.Add(out == 0)
        return out

    out = model.NewBoolVar(name)
    model.AddBoolOr(literals).OnlyEnforceIf(out)
    for literal in literals:
        model.Add(literal == 0).OnlyEnforceIf(out.Not())
    return out


def add_kitchen_hallway_back_wall_setback_constraint(
    model: Any,
    rooms: list[Room],
    floor_height: int,
    min_gap: int = KITCHEN_HALLWAY_BACK_WALL_SETBACK_MIN_GAP,
    max_gap: int = KITCHEN_HALLWAY_BACK_WALL_SETBACK_MAX_GAP,
) -> None:
    """Ensure at least one kitchen/hallway back wall has clear setback behind it."""
    min_gap = max(1, int(min_gap))
    max_gap = max(min_gap, int(max_gap))

    target_rooms = [
        room for room in rooms if str(room.type).lower() in {"kitchen", "hallway"}
    ]
    if not target_rooms:
        return

    floor_h = max(1, int(floor_height))
    candidate_clear_literals: list[cp_model.IntVar] = []

    for room in target_rooms:
        assert room.x is not None and room.y_end is not None
        assert room.x_end is not None and room.y is not None

        top_gap = model.NewIntVar(0, floor_h, f"bkset_{room.name}_top_gap")
        model.Add(top_gap == floor_h - room.y_end)

        # Selected candidate must preserve a practical door setback depth.
        room_clear = model.NewBoolVar(f"bkset_{room.name}_back_clear")
        model.Add(top_gap >= min_gap).OnlyEnforceIf(room_clear)
        model.Add(top_gap <= max_gap).OnlyEnforceIf(room_clear)

        blockers: list[cp_model.IntVar] = []
        for other in rooms:
            if other is room:
                continue

            assert other.x is not None and other.x_end is not None
            assert other.y is not None and other.y_end is not None

            x_overlap = _axis_overlap_bool(
                model,
                room.x,
                room.x_end,
                other.x,
                other.x_end,
                f"bkset_{room.name}_{other.name}_x_overlap",
            )

            # Other room intrudes if it enters the strip:
            # y in (room.y_end, room.y_end + min_gap).
            other_starts_before_limit = _ordered_bool(
                model,
                other.y,
                room.y_end + min_gap,
                f"bkset_{room.name}_{other.name}_starts_before_limit",
            )
            room_back_before_other_end = _ordered_bool(
                model,
                room.y_end,
                other.y_end,
                f"bkset_{room.name}_{other.name}_back_before_other_end",
            )
            y_intrudes = _and_of_literals(
                model,
                other_starts_before_limit,
                room_back_before_other_end,
                f"bkset_{room.name}_{other.name}_y_intrudes",
            )

            blockers.append(
                _and_of_literals(
                    model,
                    x_overlap,
                    y_intrudes,
                    f"bkset_{room.name}_{other.name}_blocker",
                )
            )

        has_blocker = _or_of_literals(model, blockers, f"bkset_{room.name}_has_blocker")
        model.Add(has_blocker == 0).OnlyEnforceIf(room_clear)
        candidate_clear_literals.append(room_clear)

    model.AddBoolOr(candidate_clear_literals)

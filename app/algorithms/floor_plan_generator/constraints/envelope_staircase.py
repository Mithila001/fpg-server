from __future__ import annotations

from ortools.sat.python import cp_model

from ..solver_models.room import Room
from app.core.config_fpg import (
    ENVELOPE_MIN_GAP,
    ENVELOPE_MAX_GAP,
    ENVELOPE_EXCLUDE_TYPES,
    ENVELOPE_APPLY_SIDES,
)


_SIDE_VALUES = {str(side).lower() for side in ENVELOPE_APPLY_SIDES}


def _non_empty_sides(apply_sides: set[str]) -> set[str]:
    sides = {side.lower() for side in apply_sides if side}
    return sides.intersection(_SIDE_VALUES)


def _axis_overlap_bool(
    model: cp_model.CpModel,
    a_start: cp_model.IntVar,
    a_end: cp_model.IntVar,
    b_start: cp_model.IntVar,
    b_end: cp_model.IntVar,
    name: str,
) -> cp_model.BoolVar:
    """Return a BoolVar indicating strict positive overlap on one axis."""
    overlap = model.NewBoolVar(name)

    a_before_b = model.NewBoolVar(f"{name}_a_before_b")
    b_before_a = model.NewBoolVar(f"{name}_b_before_a")

    model.Add(a_end <= b_start).OnlyEnforceIf(a_before_b)
    model.Add(a_end >= b_start + 1).OnlyEnforceIf(a_before_b.Not())

    model.Add(b_end <= a_start).OnlyEnforceIf(b_before_a)
    model.Add(b_end >= a_start + 1).OnlyEnforceIf(b_before_a.Not())

    # overlap == not(a_before_b or b_before_a)
    model.AddBoolOr([a_before_b, b_before_a]).OnlyEnforceIf(overlap.Not())
    model.Add(a_before_b == 0).OnlyEnforceIf(overlap)
    model.Add(b_before_a == 0).OnlyEnforceIf(overlap)

    return overlap


def _ordered_bool(
    model: cp_model.CpModel,
    lhs: cp_model.IntVar,
    rhs: cp_model.IntVar,
    strict_less_name: str,
) -> cp_model.BoolVar:
    """Bool for lhs < rhs using reified linear constraints."""
    lhs_less_rhs = model.NewBoolVar(strict_less_name)
    model.Add(lhs <= rhs - 1).OnlyEnforceIf(lhs_less_rhs)
    model.Add(lhs >= rhs).OnlyEnforceIf(lhs_less_rhs.Not())
    return lhs_less_rhs


def _or_of_literals(
    model: cp_model.CpModel,
    literals: list[cp_model.BoolVar],
    name: str,
) -> cp_model.BoolVar:
    """Create bool == OR(literals)."""
    if not literals:
        literal = model.NewBoolVar(name)
        model.Add(literal == 0)
        return literal

    out = model.NewBoolVar(name)
    model.AddBoolOr(literals).OnlyEnforceIf(out)
    for literal in literals:
        model.Add(literal == 0).OnlyEnforceIf(out.Not())
    return out


def _and_of_literals(
    model: cp_model.CpModel,
    left: cp_model.BoolVar,
    right: cp_model.BoolVar,
    name: str,
) -> cp_model.BoolVar:
    out = model.NewBoolVar(name)
    model.AddBoolAnd([left, right]).OnlyEnforceIf(out)
    model.AddBoolOr([left.Not(), right.Not()]).OnlyEnforceIf(out.Not())
    return out


def _enforce_positive_gap_bounds(
    model: cp_model.CpModel,
    gap_var: cp_model.IntVar,
    is_exterior: cp_model.BoolVar,
    min_gap: int,
    max_gap: int,
    prefix: str,
) -> None:
    """If room is exterior and gap > 0, force min_gap <= gap <= max_gap."""
    gap_positive = model.NewBoolVar(f"{prefix}_gap_positive")
    model.Add(gap_var >= 1).OnlyEnforceIf(gap_positive)
    model.Add(gap_var == 0).OnlyEnforceIf(gap_positive.Not())

    exterior_positive = _and_of_literals(
        model,
        is_exterior,
        gap_positive,
        name=f"{prefix}_exterior_positive",
    )
    model.Add(gap_var >= min_gap).OnlyEnforceIf(exterior_positive)
    model.Add(gap_var <= max_gap).OnlyEnforceIf(exterior_positive)


def add_envelope_staircase_constraints(
    model: cp_model.CpModel,
    rooms: list[Room],
    floor_width: int,
    floor_height: int,
    min_gap: int = ENVELOPE_MIN_GAP,
    max_gap: int = ENVELOPE_MAX_GAP,
    exclude_types: set[str] | None = None,
    apply_sides: set[str] | None = None,
) -> None:
    """Bound staircase-like outer-wall recess depth on selected envelope sides.

    Semantics:
    - Determine exterior rooms per side from pairwise blockers (same orthogonal span,
      another room farther outward on that side).
    - For exterior rooms only, if recess depth from side facade line is positive,
      enforce min_gap <= depth <= max_gap.
    - Zero-depth (aligned on the facade line) is always allowed.

    This is a hard constraint and can make some layouts infeasible when combined
    with tight adjacency/coverage requirements.
    """
    if min_gap < 1:
        min_gap = 1
    if max_gap < min_gap:
        max_gap = min_gap

    excluded = {t.lower() for t in (exclude_types or ENVELOPE_EXCLUDE_TYPES)}
    sides = _non_empty_sides(apply_sides or ENVELOPE_APPLY_SIDES)
    if not sides:
        return

    eligible_rooms = [room for room in rooms if room.type.lower() not in excluded]
    if len(eligible_rooms) < 2:
        return

    left_outer = model.NewIntVar(0, floor_width, "envelope_left_outer")
    right_outer = model.NewIntVar(0, floor_width, "envelope_right_outer")
    bottom_outer = model.NewIntVar(0, floor_height, "envelope_bottom_outer")
    top_outer = model.NewIntVar(0, floor_height, "envelope_top_outer")

    model.AddMinEquality(left_outer, [room.x for room in eligible_rooms])
    model.AddMaxEquality(right_outer, [room.x_end for room in eligible_rooms])
    model.AddMinEquality(bottom_outer, [room.y for room in eligible_rooms])
    model.AddMaxEquality(top_outer, [room.y_end for room in eligible_rooms])

    for room in eligible_rooms:
        left_blockers: list[cp_model.BoolVar] = []
        right_blockers: list[cp_model.BoolVar] = []
        bottom_blockers: list[cp_model.BoolVar] = []
        top_blockers: list[cp_model.BoolVar] = []

        for other in eligible_rooms:
            if other is room:
                continue

            y_overlap = _axis_overlap_bool(
                model,
                room.y,
                room.y_end,
                other.y,
                other.y_end,
                f"env_{room.name}_{other.name}_y_overlap",
            )
            x_overlap = _axis_overlap_bool(
                model,
                room.x,
                room.x_end,
                other.x,
                other.x_end,
                f"env_{room.name}_{other.name}_x_overlap",
            )

            if "left" in sides:
                other_more_left = _ordered_bool(
                    model,
                    other.x,
                    room.x,
                    f"env_{room.name}_{other.name}_other_more_left",
                )
                left_blockers.append(
                    _and_of_literals(
                        model,
                        y_overlap,
                        other_more_left,
                        f"env_{room.name}_{other.name}_left_blocker",
                    )
                )

            if "right" in sides:
                room_more_right = _ordered_bool(
                    model,
                    room.x_end,
                    other.x_end,
                    f"env_{room.name}_{other.name}_other_more_right",
                )
                right_blockers.append(
                    _and_of_literals(
                        model,
                        y_overlap,
                        room_more_right,
                        f"env_{room.name}_{other.name}_right_blocker",
                    )
                )

            if "bottom" in sides:
                other_below = _ordered_bool(
                    model,
                    other.y,
                    room.y,
                    f"env_{room.name}_{other.name}_other_below",
                )
                bottom_blockers.append(
                    _and_of_literals(
                        model,
                        x_overlap,
                        other_below,
                        f"env_{room.name}_{other.name}_bottom_blocker",
                    )
                )

            if "top" in sides:
                room_below_other_top = _ordered_bool(
                    model,
                    room.y_end,
                    other.y_end,
                    f"env_{room.name}_{other.name}_other_above",
                )
                top_blockers.append(
                    _and_of_literals(
                        model,
                        x_overlap,
                        room_below_other_top,
                        f"env_{room.name}_{other.name}_top_blocker",
                    )
                )

        if "left" in sides:
            has_left_blocker = _or_of_literals(
                model,
                left_blockers,
                f"env_{room.name}_has_left_blocker",
            )
            is_left_exterior = model.NewBoolVar(f"env_{room.name}_is_left_exterior")
            model.Add(is_left_exterior + has_left_blocker == 1)

            left_gap = model.NewIntVar(0, floor_width, f"env_{room.name}_left_gap")
            model.Add(left_gap == room.x - left_outer)
            _enforce_positive_gap_bounds(
                model,
                left_gap,
                is_left_exterior,
                min_gap,
                max_gap,
                f"env_{room.name}_left",
            )

        if "right" in sides:
            has_right_blocker = _or_of_literals(
                model,
                right_blockers,
                f"env_{room.name}_has_right_blocker",
            )
            is_right_exterior = model.NewBoolVar(f"env_{room.name}_is_right_exterior")
            model.Add(is_right_exterior + has_right_blocker == 1)

            right_gap = model.NewIntVar(0, floor_width, f"env_{room.name}_right_gap")
            model.Add(right_gap == right_outer - room.x_end)
            _enforce_positive_gap_bounds(
                model,
                right_gap,
                is_right_exterior,
                min_gap,
                max_gap,
                f"env_{room.name}_right",
            )

        if "bottom" in sides:
            has_bottom_blocker = _or_of_literals(
                model,
                bottom_blockers,
                f"env_{room.name}_has_bottom_blocker",
            )
            is_bottom_exterior = model.NewBoolVar(f"env_{room.name}_is_bottom_exterior")
            model.Add(is_bottom_exterior + has_bottom_blocker == 1)

            bottom_gap = model.NewIntVar(0, floor_height, f"env_{room.name}_bottom_gap")
            model.Add(bottom_gap == room.y - bottom_outer)
            _enforce_positive_gap_bounds(
                model,
                bottom_gap,
                is_bottom_exterior,
                min_gap,
                max_gap,
                f"env_{room.name}_bottom",
            )

        if "top" in sides:
            has_top_blocker = _or_of_literals(
                model,
                top_blockers,
                f"env_{room.name}_has_top_blocker",
            )
            is_top_exterior = model.NewBoolVar(f"env_{room.name}_is_top_exterior")
            model.Add(is_top_exterior + has_top_blocker == 1)

            top_gap = model.NewIntVar(0, floor_height, f"env_{room.name}_top_gap")
            model.Add(top_gap == top_outer - room.y_end)
            _enforce_positive_gap_bounds(
                model,
                top_gap,
                is_top_exterior,
                min_gap,
                max_gap,
                f"env_{room.name}_top",
            )

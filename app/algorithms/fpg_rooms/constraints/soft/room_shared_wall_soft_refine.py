"""Soft constraint for refinement shared-wall requirements (fpgr_p_refine_1).

Penalizes rooms that don't meet the tighter shared-wall minimums during refinement.
Reuses utilities from hard constraint for overlap/touch detection consistency.
"""

from __future__ import annotations

from typing import Dict, List

from ortools.sat.python import cp_model

from app.core.fpg_rooms.config_fpg import (
    ROOM_SHARED_WALL_RULES_REFINE,
    SOFT_ROOM_SHARED_WALL_REFINE_WEIGHT,
)
from app.algorithms.fpg_rooms.constraints.hard.room_shared_wall_constraints import (
    SharedWallRule,
    _normalize_rule,
    _touch_constraints,
    _axis_overlap_length,
)

from ...solver_models.room import Room

# TODO: Look at this. Suspicious
_WIGGLE_SCALE = 1


def build_room_shared_wall_refine_penalty(
    model: cp_model.CpModel,
    rooms: List[Room],
    refine_rules: Dict[str, dict] | None = None,
    refine_weight: int | None = None,
) -> cp_model.LinearExprT:
    """Build soft penalty for refined shared-wall requirements.

    For each room type with a tighter min_walls requirement in refinement,
    penalizes rooms that achieve fewer selected shared walls than the minimum.

    Args:
        model: CP solver model.
        rooms: List of rooms to check.
        refine_rules: Optional override of refinement rules dict. Defaults to
                      ROOM_SHARED_WALL_RULES_REFINE from config.
        refine_weight: Optional override of penalty weight. Defaults to
                       SOFT_ROOM_SHARED_WALL_REFINE_WEIGHT from config.

    Returns:
        LinearExprT for the aggregated penalty cost (0 if no violations).
    """
    if refine_rules is None:
        refine_rules = ROOM_SHARED_WALL_RULES_REFINE
    if refine_weight is None:
        refine_weight = SOFT_ROOM_SHARED_WALL_REFINE_WEIGHT

    if refine_weight <= 0:
        refine_weight = 1

    # Normalize all refinement rules
    normalized_rules: Dict[str, SharedWallRule] = {}
    for room_type, raw_rule in refine_rules.items():
        normalized = _normalize_rule(raw_rule)
        if normalized is not None:
            normalized_rules[str(room_type)] = normalized

    if not normalized_rules:
        return 0  # type: ignore

    coord_ub = max(1, sum(max(room.max_w, room.max_h) for room in rooms))
    penalty_terms: List[cp_model.LinearExprT] = []

    for room in rooms:
        # Skip hallways (same as hard constraint)
        if room.type == "hallway":
            continue

        # Get refinement rule for this room type
        rule = normalized_rules.get(room.type)
        if rule is None:
            continue

        assert room.x is not None and room.y is not None
        assert room.x_end is not None and room.y_end is not None
        assert room.w is not None and room.h is not None

        side_overlap_terms: Dict[str, List[cp_model.IntVar]] = {
            "right": [],
            "left": [],
            "top": [],
            "bottom": [],
        }

        others = [other for other in rooms if other.name != room.name]
        side_total_ub = max(1, len(others)) * coord_ub

        # Detect overlaps with all neighbor rooms (same logic as hard constraint)
        for other in others:
            assert other.x is not None and other.y is not None
            assert other.x_end is not None and other.y_end is not None

            touches = _touch_constraints(model, room, other)

            vertical_overlap = _axis_overlap_length(
                model,
                room.y,
                room.y_end,
                other.y,
                other.y_end,
                coord_ub,
                f"{room.name}_{other.name}_v_sr",
            )
            horizontal_overlap = _axis_overlap_length(
                model,
                room.x,
                room.x_end,
                other.x,
                other.x_end,
                coord_ub,
                f"{room.name}_{other.name}_h_sr",
            )

            right_overlap = model.NewIntVar(
                0, coord_ub, f"sr_ov_right_{room.name}_{other.name}"
            )  # type: ignore
            left_overlap = model.NewIntVar(
                0, coord_ub, f"sr_ov_left_{room.name}_{other.name}"
            )  # type: ignore
            top_overlap = model.NewIntVar(
                0, coord_ub, f"sr_ov_top_{room.name}_{other.name}"
            )  # type: ignore
            bottom_overlap = model.NewIntVar(
                0, coord_ub, f"sr_ov_bottom_{room.name}_{other.name}"
            )  # type: ignore

            model.Add(right_overlap == vertical_overlap).OnlyEnforceIf(touches["right"])  # type: ignore
            model.Add(right_overlap == 0).OnlyEnforceIf(touches["right"].Not())  # type: ignore

            model.Add(left_overlap == vertical_overlap).OnlyEnforceIf(touches["left"])  # type: ignore
            model.Add(left_overlap == 0).OnlyEnforceIf(touches["left"].Not())  # type: ignore

            model.Add(top_overlap == horizontal_overlap).OnlyEnforceIf(touches["top"])  # type: ignore
            model.Add(top_overlap == 0).OnlyEnforceIf(touches["top"].Not())  # type: ignore

            model.Add(bottom_overlap == horizontal_overlap).OnlyEnforceIf(
                touches["bottom"]
            )  # type: ignore
            model.Add(bottom_overlap == 0).OnlyEnforceIf(touches["bottom"].Not())  # type: ignore

            side_overlap_terms["right"].append(right_overlap)
            side_overlap_terms["left"].append(left_overlap)
            side_overlap_terms["top"].append(top_overlap)
            side_overlap_terms["bottom"].append(bottom_overlap)

        side_lengths = {
            "right": room.h,
            "left": room.h,
            "top": room.w,
            "bottom": room.w,
        }

        # Determine which sides are selected (meet minimum coverage with wiggle_pct)
        selected_flags: Dict[str, cp_model.IntVar] = {}
        selected_count: List[cp_model.IntVar] = []

        for side, side_length in side_lengths.items():
            side_terms = side_overlap_terms[side]
            total_overlap = model.NewIntVar(
                0, side_total_ub, f"sr_total_ov_{room.name}_{side}"
            )  # type: ignore
            model.Add(total_overlap == cp_model.LinearExpr.Sum(side_terms))  # type: ignore

            covered_len = model.NewIntVar(0, coord_ub, f"sr_cov_len_{room.name}_{side}")  # type: ignore
            model.AddMinEquality(covered_len, [total_overlap, side_length])  # type: ignore

            selected = model.NewBoolVar(f"sr_selected_{room.name}_{side}")  # type: ignore
            selected_flags[side] = selected

            if rule.min_walls > 0:
                selected_required = model.NewIntVar(
                    0, coord_ub, f"sr_sel_req_{room.name}_{side}"
                )  # type: ignore
                model.Add(selected_required == side_length).OnlyEnforceIf(selected)  # type: ignore
                model.Add(selected_required == 0).OnlyEnforceIf(selected.Not())  # type: ignore

                selected_covered = model.NewIntVar(
                    0, coord_ub, f"sr_sel_cov_{room.name}_{side}"
                )  # type: ignore
                model.Add(selected_covered == covered_len).OnlyEnforceIf(selected)  # type: ignore
                model.Add(selected_covered == 0).OnlyEnforceIf(selected.Not())  # type: ignore

                required_scale = _WIGGLE_SCALE - rule.wiggle_pct
                model.Add(
                    _WIGGLE_SCALE * selected_covered
                    == required_scale * selected_required
                ).OnlyEnforceIf(selected)  # type: ignore

            selected_count.append(selected)

        # Count actual selected walls
        actual_selected = model.NewIntVar(0, 4, f"sr_actual_selected_{room.name}")  # type: ignore
        model.Add(actual_selected == cp_model.LinearExpr.Sum(selected_count))  # type: ignore

        # Penalty: max(0, min_walls - actual_selected) * weight
        # This is implemented as an IntVar that captures the shortfall
        if rule.min_walls > 0:
            shortfall = model.NewIntVar(0, 4, f"sr_shortfall_{room.name}")  # type: ignore
            model.Add(shortfall >= rule.min_walls - actual_selected)  # type: ignore
            model.Add(shortfall >= 0)  # type: ignore
            penalty_terms.append(shortfall * refine_weight)

    if not penalty_terms:
        return 0  # type: ignore

    return cp_model.LinearExpr.Sum(penalty_terms)  # type: ignore

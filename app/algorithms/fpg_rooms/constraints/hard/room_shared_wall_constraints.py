"""Per-room shared-wall hard constraints for non-hallway rooms."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from ortools.sat.python import cp_model

from app.core.fpg_rooms.config_fpg import ROOM_SHARED_WALL_RULES

from ...solver_models.room import Room

_WIGGLE_SCALE = 1


@dataclass(frozen=True)
class SharedWallRule:
    min_walls: int
    max_walls: int
    wiggle_pct: int


def _normalize_rule(raw_rule: object) -> SharedWallRule | None:
    if not isinstance(raw_rule, dict):
        return None

    min_walls = int(raw_rule.get("min_walls", 0))
    max_walls = int(raw_rule.get("max_walls", 4))
    wiggle_pct = int(raw_rule.get("wiggle_pct", 0))

    min_walls = max(0, min(4, min_walls))
    max_walls = max(0, min(4, max_walls))
    if min_walls > max_walls:
        min_walls = max_walls

    wiggle_pct = max(0, min(100, wiggle_pct))
    return SharedWallRule(
        min_walls=min_walls, max_walls=max_walls, wiggle_pct=wiggle_pct
    )


def _touch_constraints(
    model: Any,
    room1: Room,
    room2: Room,
) -> Dict[str, cp_model.IntVar]:
    suffix = f"{room1.name}_{room2.name}"

    touch_right = model.NewBoolVar(f"rs_tr_{suffix}")  # type: ignore
    touch_left = model.NewBoolVar(f"rs_tl_{suffix}")  # type: ignore
    touch_top = model.NewBoolVar(f"rs_tt_{suffix}")  # type: ignore
    touch_bottom = model.NewBoolVar(f"rs_tb_{suffix}")  # type: ignore

    model.Add(room1.x == room2.x_end).OnlyEnforceIf(touch_right)  # type: ignore
    model.Add(room1.x_end == room2.x).OnlyEnforceIf(touch_left)  # type: ignore
    model.Add(room1.y == room2.y_end).OnlyEnforceIf(touch_top)  # type: ignore
    model.Add(room1.y_end == room2.y).OnlyEnforceIf(touch_bottom)  # type: ignore

    return {
        "right": touch_right,
        "left": touch_left,
        "top": touch_top,
        "bottom": touch_bottom,
    }


def _axis_overlap_length(
    model: Any,
    start1: cp_model.IntVar,
    end1: cp_model.IntVar,
    start2: cp_model.IntVar,
    end2: cp_model.IntVar,
    coord_ub: int,
    suffix: str,
) -> cp_model.IntVar:
    overlap_start = model.NewIntVar(0, coord_ub, f"rs_ov_start_{suffix}")  # type: ignore
    overlap_end = model.NewIntVar(0, coord_ub, f"rs_ov_end_{suffix}")  # type: ignore
    model.AddMaxEquality(overlap_start, [start1, start2])  # type: ignore
    model.AddMinEquality(overlap_end, [end1, end2])  # type: ignore

    overlap_raw = model.NewIntVar(-coord_ub, coord_ub, f"rs_ov_raw_{suffix}")  # type: ignore
    model.Add(overlap_raw == overlap_end - overlap_start)  # type: ignore

    overlap_len = model.NewIntVar(0, coord_ub, f"rs_ov_len_{suffix}")  # type: ignore
    model.AddMaxEquality(overlap_len, [overlap_raw, 0])  # type: ignore
    return overlap_len


def add_room_shared_wall_constraints(
    model: Any,
    rooms: List[Room],
) -> None:
    normalized_rules: Dict[str, SharedWallRule] = {}
    for room_type, raw_rule in ROOM_SHARED_WALL_RULES.items():
        normalized = _normalize_rule(raw_rule)
        if normalized is not None:
            normalized_rules[str(room_type)] = normalized

    if not normalized_rules:
        return

    coord_ub = max(1, sum(max(room.max_w, room.max_h) for room in rooms))

    for room in rooms:
        if room.type == "hallway":
            continue

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
                f"{room.name}_{other.name}_v",
            )
            horizontal_overlap = _axis_overlap_length(
                model,
                room.x,
                room.x_end,
                other.x,
                other.x_end,
                coord_ub,
                f"{room.name}_{other.name}_h",
            )

            right_overlap = model.NewIntVar(
                0, coord_ub, f"rs_ov_right_{room.name}_{other.name}"
            )  # type: ignore
            left_overlap = model.NewIntVar(
                0, coord_ub, f"rs_ov_left_{room.name}_{other.name}"
            )  # type: ignore
            top_overlap = model.NewIntVar(
                0, coord_ub, f"rs_ov_top_{room.name}_{other.name}"
            )  # type: ignore
            bottom_overlap = model.NewIntVar(
                0, coord_ub, f"rs_ov_bottom_{room.name}_{other.name}"
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

        fully_shared_sides: List[cp_model.IntVar] = []
        selected_flags: Dict[str, cp_model.IntVar] = {}
        selected_required_terms: List[cp_model.IntVar] = []
        selected_covered_terms: List[cp_model.IntVar] = []

        for side, side_length in side_lengths.items():
            side_terms = side_overlap_terms[side]
            total_overlap = model.NewIntVar(
                0, side_total_ub, f"rs_total_ov_{room.name}_{side}"
            )  # type: ignore
            model.Add(total_overlap == cp_model.LinearExpr.Sum(side_terms))  # type: ignore

            covered_len = model.NewIntVar(0, coord_ub, f"rs_cov_len_{room.name}_{side}")  # type: ignore
            model.AddMinEquality(covered_len, [total_overlap, side_length])  # type: ignore

            fully_shared = model.NewBoolVar(f"rs_fully_shared_{room.name}_{side}")  # type: ignore
            model.Add(total_overlap >= side_length).OnlyEnforceIf(fully_shared)  # type: ignore
            model.Add(total_overlap <= side_length - 1).OnlyEnforceIf(
                fully_shared.Not()
            )  # type: ignore
            fully_shared_sides.append(fully_shared)

            selected = model.NewBoolVar(f"rs_selected_{room.name}_{side}")  # type: ignore
            selected_flags[side] = selected

            selected_required = model.NewIntVar(
                0, coord_ub, f"rs_sel_req_{room.name}_{side}"
            )  # type: ignore
            model.Add(selected_required == side_length).OnlyEnforceIf(selected)  # type: ignore
            model.Add(selected_required == 0).OnlyEnforceIf(selected.Not())  # type: ignore
            selected_required_terms.append(selected_required)

            selected_covered = model.NewIntVar(
                0, coord_ub, f"rs_sel_cov_{room.name}_{side}"
            )  # type: ignore
            model.Add(selected_covered == covered_len).OnlyEnforceIf(selected)  # type: ignore
            model.Add(selected_covered == 0).OnlyEnforceIf(selected.Not())  # type: ignore
            selected_covered_terms.append(selected_covered)

        model.Add(cp_model.LinearExpr.Sum(fully_shared_sides) <= rule.max_walls)  # type: ignore

        if rule.min_walls > 0:
            model.Add(
                cp_model.LinearExpr.Sum(list(selected_flags.values())) == rule.min_walls
            )  # type: ignore

            selected_required_len = model.NewIntVar(
                0, 4 * coord_ub, f"rs_req_len_{room.name}"
            )  # type: ignore
            selected_covered_len = model.NewIntVar(
                0, 4 * coord_ub, f"rs_cov_len_{room.name}"
            )  # type: ignore
            model.Add(
                selected_required_len
                == cp_model.LinearExpr.Sum(selected_required_terms)
            )  # type: ignore
            model.Add(
                selected_covered_len == cp_model.LinearExpr.Sum(selected_covered_terms)
            )  # type: ignore

            required_scale = _WIGGLE_SCALE - rule.wiggle_pct
            model.Add(
                _WIGGLE_SCALE * selected_covered_len
                >= required_scale * selected_required_len
            )
        else:
            model.Add(cp_model.LinearExpr.Sum(list(selected_flags.values())) == 0)  # type: ignore

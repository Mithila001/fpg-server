"""
Hallway constraints for the floor plan generator.
"""

from ortools.sat.python import cp_model
from typing import List, Dict, Any

from ..solver_models.room import Room
from app.core.fpg_rooms.config_fpg import (
    HALLWAY_WIDTH,
    HALLWAY_MIN_LENGTH,
    HALLWAY_REQUIRED_SHARED_WALLS,
)

# Minimum shared-edge length required for a hallway ↔ room connection.
# Set to HALLWAY_WIDTH so the requirement is always satisfiable even when the
# hallway touches a room on its narrow face.
_MIN_OVERLAP = HALLWAY_WIDTH


def _touch_constraints(
    model: cp_model.CpModel,
    room1: Room,
    room2: Room,
    enforcer=None,
    require_touch: bool = True,
) -> Dict[str, cp_model.IntVar]:
    """Add touch constraints between room1 and room2.

    Returns side-touch BoolVars keyed by side name.
    """
    suffix = f"{room1.name}_{room2.name}"

    touch_right = model.NewBoolVar(f"h_tr_{suffix}")  # type: ignore
    touch_left = model.NewBoolVar(f"h_tl_{suffix}")  # type: ignore
    touch_top = model.NewBoolVar(f"h_tt_{suffix}")  # type: ignore
    touch_bottom = model.NewBoolVar(f"h_tb_{suffix}")  # type: ignore

    conds: list = [] if enforcer is None else [enforcer]

    # ── Channelling: BoolVar is True iff the corresponding face equality holds ─
    model.Add(room1.x == room2.x_end).OnlyEnforceIf(conds + [touch_right])  # type: ignore
    model.Add(room1.x_end == room2.x).OnlyEnforceIf(conds + [touch_left])  # type: ignore
    model.Add(room1.y == room2.y_end).OnlyEnforceIf(conds + [touch_top])  # type: ignore
    model.Add(room1.y_end == room2.y).OnlyEnforceIf(conds + [touch_bottom])  # type: ignore

    # ── At least one direction must be active when requested ─────────────────
    all_touch = [touch_right, touch_left, touch_top, touch_bottom]
    if require_touch:
        if enforcer is None:
            model.AddBoolOr(all_touch)  # type: ignore
        else:
            model.AddBoolOr(all_touch).OnlyEnforceIf(enforcer)  # type: ignore

    # ── Minimum shared-edge overlap ───────────────────────────────────────────
    # Vertical face touches (right/left) → y-extents must overlap
    for t in (touch_right, touch_left):
        model.Add(room1.y + _MIN_OVERLAP <= room2.y_end).OnlyEnforceIf(conds + [t])  # type: ignore
        model.Add(room2.y + _MIN_OVERLAP <= room1.y_end).OnlyEnforceIf(conds + [t])  # type: ignore

    # Horizontal face touches (top/bottom) → x-extents must overlap
    for t in (touch_top, touch_bottom):
        model.Add(room1.x + _MIN_OVERLAP <= room2.x_end).OnlyEnforceIf(conds + [t])  # type: ignore
        model.Add(room2.x + _MIN_OVERLAP <= room1.x_end).OnlyEnforceIf(conds + [t])  # type: ignore

    return {
        "right": touch_right,
        "left": touch_left,
        "top": touch_top,
        "bottom": touch_bottom,
    }


def _axis_overlap_length(
    model: cp_model.CpModel,
    start1: cp_model.IntVar,
    end1: cp_model.IntVar,
    start2: cp_model.IntVar,
    end2: cp_model.IntVar,
    coord_ub: int,
    suffix: str,
) -> cp_model.IntVar:
    """Return max(0, min(end1, end2) - max(start1, start2))."""
    overlap_start = model.NewIntVar(0, coord_ub, f"ov_start_{suffix}")  # type: ignore
    overlap_end = model.NewIntVar(0, coord_ub, f"ov_end_{suffix}")  # type: ignore
    model.AddMaxEquality(overlap_start, [start1, start2])  # type: ignore
    model.AddMinEquality(overlap_end, [end1, end2])  # type: ignore

    overlap_raw = model.NewIntVar(-coord_ub, coord_ub, f"ov_raw_{suffix}")  # type: ignore
    model.Add(overlap_raw == overlap_end - overlap_start)  # type: ignore

    overlap_len = model.NewIntVar(0, coord_ub, f"ov_len_{suffix}")  # type: ignore
    model.AddMaxEquality(overlap_len, [overlap_raw, 0])  # type: ignore
    return overlap_len


def add_hallway_constraints(
    model: cp_model.CpModel,
    rooms: List[Room],
) -> Dict[str, Any]:
    """Apply hallway-specific constraints and return hallway metadata.

    Enforces hallway geometry rules (fixed-width/scalable-length), required
    living-room connection, at least one additional non-living-room
    connection, and minimum fully-covered hallway walls.

    Args:
        model: CP-SAT model to add constraints to.
        rooms: List of all rooms including hallway rooms.

    Returns:
        Dict with keys:
        - 'hallway_rooms': list of hallway room objects processed

        Returns empty dict if no hallways are present.
    """
    hallways = [r for r in rooms if r.type == "hallway"]
    if not hallways:
        return {}

    non_hallways = [r for r in rooms if r.type != "hallway"]
    coord_ub = max(1, sum(max(r.max_w, r.max_h) for r in rooms))
    
    living_rooms = [r for r in non_hallways if r.type == "livingRoom"]
    living_room = living_rooms[0] if living_rooms else None
    
    non_living_rooms = [r for r in non_hallways if r.type != "livingRoom"]

    for hallway in hallways:
        assert hallway.w is not None and hallway.h is not None
        assert hallway.x is not None and hallway.y is not None
        assert hallway.x_end is not None and hallway.y_end is not None

        pair_touches: Dict[str, Dict[str, cp_model.IntVar]] = {}
        side_overlap_terms: Dict[str, List[cp_model.IntVar]] = {
            "right": [],
            "left": [],
            "top": [],
            "bottom": [],
        }

        for room in non_hallways:
            assert room.x is not None and room.y is not None
            assert room.x_end is not None and room.y_end is not None

            touches = _touch_constraints(
                model,
                hallway,
                room,
                require_touch=False,
            )
            pair_touches[room.name] = touches

            vertical_overlap = _axis_overlap_length(
                model,
                hallway.y,
                hallway.y_end,
                room.y,
                room.y_end,
                coord_ub,
                f"{hallway.name}_{room.name}_v",
            )
            horizontal_overlap = _axis_overlap_length(
                model,
                hallway.x,
                hallway.x_end,
                room.x,
                room.x_end,
                coord_ub,
                f"{hallway.name}_{room.name}_h",
            )

            right_overlap = model.NewIntVar(0, coord_ub, f"h_ov_right_{hallway.name}_{room.name}")  # type: ignore
            left_overlap = model.NewIntVar(0, coord_ub, f"h_ov_left_{hallway.name}_{room.name}")  # type: ignore
            top_overlap = model.NewIntVar(0, coord_ub, f"h_ov_top_{hallway.name}_{room.name}")  # type: ignore
            bottom_overlap = model.NewIntVar(0, coord_ub, f"h_ov_bottom_{hallway.name}_{room.name}")  # type: ignore

            model.Add(right_overlap == vertical_overlap).OnlyEnforceIf(touches["right"])  # type: ignore
            model.Add(right_overlap == 0).OnlyEnforceIf(touches["right"].Not())  # type: ignore

            model.Add(left_overlap == vertical_overlap).OnlyEnforceIf(touches["left"])  # type: ignore
            model.Add(left_overlap == 0).OnlyEnforceIf(touches["left"].Not())  # type: ignore

            model.Add(top_overlap == horizontal_overlap).OnlyEnforceIf(touches["top"])  # type: ignore
            model.Add(top_overlap == 0).OnlyEnforceIf(touches["top"].Not())  # type: ignore

            model.Add(bottom_overlap == horizontal_overlap).OnlyEnforceIf(touches["bottom"])  # type: ignore
            model.Add(bottom_overlap == 0).OnlyEnforceIf(touches["bottom"].Not())  # type: ignore

            side_overlap_terms["right"].append(right_overlap)
            side_overlap_terms["left"].append(left_overlap)
            side_overlap_terms["top"].append(top_overlap)
            side_overlap_terms["bottom"].append(bottom_overlap)

        # ── Rule 1: Fixed-width / scalable-length shape ───────────────────────
        is_horizontal = model.NewBoolVar(f"{hallway.name}_is_horizontal")  # type: ignore

        # Horizontal: w is the long, free side; h is the fixed narrow side
        model.Add(hallway.w >= HALLWAY_MIN_LENGTH).OnlyEnforceIf(  # type: ignore[attr-defined]
            is_horizontal
        )
        model.Add(hallway.h == HALLWAY_WIDTH).OnlyEnforceIf(  # type: ignore[attr-defined]
            is_horizontal
        )

        # Vertical: h is the long, free side; w is the fixed narrow side
        model.Add(hallway.h >= HALLWAY_MIN_LENGTH).OnlyEnforceIf(  # type: ignore[attr-defined]
            is_horizontal.Not()
        )
        model.Add(hallway.w == HALLWAY_WIDTH).OnlyEnforceIf(  # type: ignore[attr-defined]
            is_horizontal.Not()
        )

        # ── Rule 2: Living-room connection (always required) ──────────────────
        if living_room is not None:
            living_touches = pair_touches.get(living_room.name)
            assert living_touches is not None
            model.AddBoolOr(list(living_touches.values()))  # type: ignore
        else:
            # Hallway requires a living room to connect to.
            model.AddBoolOr([])

        # ── Rule 3: Must touch at least one non-living room ───────────────────
        if non_living_rooms:
            touches_non_living: List[cp_model.IntVar] = []
            for room in non_living_rooms:
                room_touches = pair_touches.get(room.name)
                assert room_touches is not None
                touches_non_living.extend(list(room_touches.values()))

            model.AddBoolOr(touches_non_living)  # type: ignore
        else:
            # Hallway requires at least one non-living room to connect to.
            model.AddBoolOr([])

        # ── Rule 4: At least N hallway walls must be fully covered ────────────
        required_shared_walls = max(0, min(4, int(HALLWAY_REQUIRED_SHARED_WALLS)))
        hallway_side_covered: List[cp_model.IntVar] = []
        side_lengths = {
            "right": hallway.h,
            "left": hallway.h,
            "top": hallway.w,
            "bottom": hallway.w,
        }

        for side, side_length in side_lengths.items():
            covered = model.NewBoolVar(f"{hallway.name}_{side}_covered")  # type: ignore
            hallway_side_covered.append(covered)
            side_terms = side_overlap_terms[side]

            if not side_terms:
                model.Add(covered == 0)  # type: ignore
                continue

            total_overlap = cp_model.LinearExpr.Sum(side_terms)
            model.Add(total_overlap >= side_length).OnlyEnforceIf(covered)  # type: ignore
            model.Add(total_overlap <= side_length - 1).OnlyEnforceIf(covered.Not())  # type: ignore

        model.Add(cp_model.LinearExpr.Sum(hallway_side_covered) >= required_shared_walls)  # type: ignore

    return {
        "hallway_rooms": hallways,
    }

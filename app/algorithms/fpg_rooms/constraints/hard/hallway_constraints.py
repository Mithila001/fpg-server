"""Hallway hard constraints for the floor plan generator."""

from typing import Any, Dict, List

from ortools.sat.python import cp_model

from app.core.fpg_rooms.config_fpg import (
    HALLWAY_LONG_SIDE_MIN,
    HALLWAY_REQUIRED_SHARED_WALLS,
    HALLWAY_NARROW_SIDE_MIN,
    HALLWAY_NARROW_SIDE_MAX,
    MIN_OVERLAP,
)

from ...solver_models.room import Room


def _touch_constraints(
    model: Any,
    room1: Room,
    room2: Room,
    enforcer=None,
    require_touch: bool = True,
) -> Dict[str, cp_model.IntVar]:
    suffix = f"{room1.name}_{room2.name}"

    touch_right = model.NewBoolVar(f"h_tr_{suffix}")  # type: ignore
    touch_left = model.NewBoolVar(f"h_tl_{suffix}")  # type: ignore
    touch_top = model.NewBoolVar(f"h_tt_{suffix}")  # type: ignore
    touch_bottom = model.NewBoolVar(f"h_tb_{suffix}")  # type: ignore

    conds: list = [] if enforcer is None else [enforcer]

    model.Add(room1.x == room2.x_end).OnlyEnforceIf(conds + [touch_right])  # type: ignore
    model.Add(room1.x_end == room2.x).OnlyEnforceIf(conds + [touch_left])  # type: ignore
    model.Add(room1.y == room2.y_end).OnlyEnforceIf(conds + [touch_top])  # type: ignore
    model.Add(room1.y_end == room2.y).OnlyEnforceIf(conds + [touch_bottom])  # type: ignore

    all_touch = [touch_right, touch_left, touch_top, touch_bottom]
    if require_touch:
        if enforcer is None:
            model.AddBoolOr(all_touch)  # type: ignore
        else:
            model.AddBoolOr(all_touch).OnlyEnforceIf(enforcer)  # type: ignore

    for touch in (touch_right, touch_left):
        model.Add(room1.y + MIN_OVERLAP <= room2.y_end).OnlyEnforceIf(conds + [touch])  # type: ignore
        model.Add(room2.y + MIN_OVERLAP <= room1.y_end).OnlyEnforceIf(conds + [touch])  # type: ignore

    for touch in (touch_top, touch_bottom):
        model.Add(room1.x + MIN_OVERLAP <= room2.x_end).OnlyEnforceIf(conds + [touch])  # type: ignore
        model.Add(room2.x + MIN_OVERLAP <= room1.x_end).OnlyEnforceIf(conds + [touch])  # type: ignore

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
    model: Any,
    rooms: List[Room],
) -> Dict[str, Any]:
    hallways = [room for room in rooms if room.type == "hallway"]
    if not hallways:
        return {}

    non_hallways = [room for room in rooms if room.type != "hallway"]
    coord_ub = max(1, sum(max(room.max_w, room.max_h) for room in rooms))

    living_rooms = [room for room in non_hallways if room.type == "livingRoom"]
    living_room = living_rooms[0] if living_rooms else None

    non_living_rooms = [room for room in non_hallways if room.type != "livingRoom"]

    # Map to hold whether each hallway directly touches the living room
    hallway_touches_living: Dict[str, cp_model.IntVar] = {}

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

            touches = _touch_constraints(model, hallway, room, require_touch=False)
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

            right_overlap = model.NewIntVar(
                0, coord_ub, f"h_ov_right_{hallway.name}_{room.name}"
            )  # type: ignore
            left_overlap = model.NewIntVar(
                0, coord_ub, f"h_ov_left_{hallway.name}_{room.name}"
            )  # type: ignore
            top_overlap = model.NewIntVar(
                0, coord_ub, f"h_ov_top_{hallway.name}_{room.name}"
            )  # type: ignore
            bottom_overlap = model.NewIntVar(
                0, coord_ub, f"h_ov_bottom_{hallway.name}_{room.name}"
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

        is_horizontal = model.NewBoolVar(f"{hallway.name}_is_horizontal")  # type: ignore

        model.Add(hallway.w >= HALLWAY_LONG_SIDE_MIN).OnlyEnforceIf(is_horizontal)  # type: ignore[attr-defined]
        model.Add(hallway.h >= HALLWAY_NARROW_SIDE_MIN).OnlyEnforceIf(is_horizontal)  # type: ignore[attr-defined]
        model.Add(hallway.h <= HALLWAY_NARROW_SIDE_MAX).OnlyEnforceIf(is_horizontal)  # type: ignore[attr-defined]

        model.Add(hallway.h >= HALLWAY_LONG_SIDE_MIN).OnlyEnforceIf(is_horizontal.Not())  # type: ignore[attr-defined]
        model.Add(hallway.w >= HALLWAY_NARROW_SIDE_MIN).OnlyEnforceIf(
            is_horizontal.Not()
        )  # type: ignore[attr-defined]
        model.Add(hallway.w <= HALLWAY_NARROW_SIDE_MAX).OnlyEnforceIf(
            is_horizontal.Not()
        )  # type: ignore[attr-defined]

        # Build a boolean that represents whether this hallway directly touches the living room
        touches_living = model.NewBoolVar(f"{hallway.name}_touches_living")  # type: ignore
        hallway_touches_living[hallway.name] = touches_living
        if living_room is not None:
            living_touches = pair_touches.get(living_room.name)
            assert living_touches is not None
            # If any of the side-touch booleans is true, then touches_living must be true
            for t in list(living_touches.values()):
                model.AddImplication(t, touches_living)  # type: ignore
            # touches_living implies at least one of the touch booleans
            model.AddBoolOr(list(living_touches.values()) + [touches_living.Not()])  # type: ignore
        else:
            model.Add(touches_living == 0)  # type: ignore

        if non_living_rooms:
            touches_non_living: List[cp_model.IntVar] = []
            for room in non_living_rooms:
                room_touches = pair_touches.get(room.name)
                assert room_touches is not None
                touches_non_living.extend(list(room_touches.values()))
            model.AddBoolOr(touches_non_living)  # type: ignore
        else:
            model.AddBoolOr([])

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

        model.Add(
            cp_model.LinearExpr.Sum(hallway_side_covered) >= required_shared_walls
        )  # type: ignore

    # Second pass: allow a hallway to satisfy the living-room attachment
    # by touching another hallway that itself touches the living room.
    for hallway in hallways:
        touches_living = hallway_touches_living.get(hallway.name)
        assert touches_living is not None

        # Ensure coordinates are present for typing/static checks
        assert hallway.x is not None and hallway.y is not None
        assert hallway.x_end is not None and hallway.y_end is not None

        candidates_and_living: List[cp_model.IntVar] = []
        for other in hallways:
            if other.name == hallway.name:
                continue

            # touch booleans between hallway and other hallway
            hh_touches = _touch_constraints(model, hallway, other, require_touch=False)

            # compute per-axis overlap lengths
            # Ensure the other hallway has coordinates
            assert other.x is not None and other.y is not None
            assert other.x_end is not None and other.y_end is not None

            hh_vertical_overlap = _axis_overlap_length(
                model,
                hallway.y,
                hallway.y_end,
                other.y,
                other.y_end,
                coord_ub,
                f"{hallway.name}_{other.name}_v",
            )
            hh_horizontal_overlap = _axis_overlap_length(
                model,
                hallway.x,
                hallway.x_end,
                other.x,
                other.x_end,
                coord_ub,
                f"{hallway.name}_{other.name}_h",
            )

            # per-side overlap IntVars (only non-zero when the corresponding touch holds)
            hh_right_overlap = model.NewIntVar(
                0, coord_ub, f"hh_ov_right_{hallway.name}_{other.name}"
            )  # type: ignore
            hh_left_overlap = model.NewIntVar(
                0, coord_ub, f"hh_ov_left_{hallway.name}_{other.name}"
            )  # type: ignore
            hh_top_overlap = model.NewIntVar(
                0, coord_ub, f"hh_ov_top_{hallway.name}_{other.name}"
            )  # type: ignore
            hh_bottom_overlap = model.NewIntVar(
                0, coord_ub, f"hh_ov_bottom_{hallway.name}_{other.name}"
            )  # type: ignore

            model.Add(hh_right_overlap == hh_vertical_overlap).OnlyEnforceIf(
                hh_touches["right"]
            )  # type: ignore
            model.Add(hh_right_overlap == 0).OnlyEnforceIf(hh_touches["right"].Not())  # type: ignore

            model.Add(hh_left_overlap == hh_vertical_overlap).OnlyEnforceIf(
                hh_touches["left"]
            )  # type: ignore
            model.Add(hh_left_overlap == 0).OnlyEnforceIf(hh_touches["left"].Not())  # type: ignore

            model.Add(hh_top_overlap == hh_horizontal_overlap).OnlyEnforceIf(
                hh_touches["top"]
            )  # type: ignore
            model.Add(hh_top_overlap == 0).OnlyEnforceIf(hh_touches["top"].Not())  # type: ignore

            model.Add(hh_bottom_overlap == hh_horizontal_overlap).OnlyEnforceIf(
                hh_touches["bottom"]
            )  # type: ignore
            model.Add(hh_bottom_overlap == 0).OnlyEnforceIf(hh_touches["bottom"].Not())  # type: ignore

            # For each side, a boolean indicating overlap meets MIN_OVERLAP
            side_overlap_meets: List[cp_model.IntVar] = []
            side_candidates: List[cp_model.IntVar] = []

            for side_name, overlap_var in (
                ("right", hh_right_overlap),
                ("left", hh_left_overlap),
                ("top", hh_top_overlap),
                ("bottom", hh_bottom_overlap),
            ):
                meet_var = model.NewBoolVar(
                    f"hh_{hallway.name}_{other.name}_{side_name}_meets"
                )  # type: ignore
                side_overlap_meets.append(meet_var)
                # overlap >= MIN_OVERLAP <=> meet_var true
                model.Add(overlap_var >= MIN_OVERLAP).OnlyEnforceIf(meet_var)  # type: ignore
                model.Add(overlap_var <= MIN_OVERLAP - 1).OnlyEnforceIf(meet_var.Not())  # type: ignore

                # candidate for this side: touch AND overlap meets
                side_candidate = model.NewBoolVar(
                    f"hh_{hallway.name}_{other.name}_{side_name}_candidate"
                )  # type: ignore
                side_candidates.append(side_candidate)
                # side_candidate => touch on this side
                model.AddImplication(side_candidate, hh_touches[side_name])  # type: ignore
                # side_candidate => overlap meets
                model.AddImplication(side_candidate, meet_var)  # type: ignore

            # candidate per-pair (any side)
            pair_candidate = model.NewBoolVar(
                f"hh_pair_{hallway.name}_{other.name}_candidate"
            )  # type: ignore
            if side_candidates:
                model.AddBoolOr(side_candidates + [pair_candidate.Not()])  # type: ignore
                for sc in side_candidates:
                    model.AddImplication(sc, pair_candidate)  # type: ignore
            else:
                model.Add(pair_candidate == 0)  # type: ignore

            # conjunction: pair_candidate AND other.touches_living
            other_touches_living = hallway_touches_living.get(other.name)
            assert other_touches_living is not None
            pair_and_living = model.NewBoolVar(
                f"hh_pair_and_living_{hallway.name}_{other.name}"
            )  # type: ignore
            model.AddImplication(pair_and_living, pair_candidate)  # type: ignore
            model.AddImplication(pair_and_living, other_touches_living)  # type: ignore

            candidates_and_living.append(pair_and_living)

        # touches_hallway_with_living is true if any candidate_and_living is true
        touches_hallway_with_living = model.NewBoolVar(
            f"{hallway.name}_touches_hallway_with_living"
        )  # type: ignore
        if candidates_and_living:
            model.AddBoolOr(candidates_and_living + [touches_hallway_with_living.Not()])  # type: ignore
            for c in candidates_and_living:
                model.AddImplication(c, touches_hallway_with_living)  # type: ignore
        else:
            model.Add(touches_hallway_with_living == 0)  # type: ignore

        # Final rule: hallway must either touch living room directly OR touch a hallway that touches living room
        model.AddBoolOr([touches_living, touches_hallway_with_living])  # type: ignore

    return {"hallway_rooms": hallways}

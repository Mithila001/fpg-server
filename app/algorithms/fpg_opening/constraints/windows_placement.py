from __future__ import annotations

from collections import defaultdict
from typing import Any

from ortools.sat.python import cp_model

from app.algorithms.types.opening import NormalizedRoom, OpeningPayload
from app.algorithms.types.opening_solver import WindowCandidate, WindowDecisionVars
from app.core.fpg_opening_config import (
    CARDINAL_SIDES,
    GEOMETRIC_TOLERANCE,
    WINDOW_ELIGIBLE_ROOM_TYPES,
    normalize_room_type,
)


def is_window_eligible_room(room_type: str) -> bool:
    return normalize_room_type(room_type) in WINDOW_ELIGIBLE_ROOM_TYPES


def _get_axis_interval(side: str, opening: dict[str, Any]) -> tuple[float, float]:
    if side in ("south", "north"):
        start = float(min(opening["x1"], opening["x2"]))
        end = float(max(opening["x1"], opening["x2"]))
        return start, end

    start = float(min(opening["y1"], opening["y2"]))
    end = float(max(opening["y1"], opening["y2"]))
    return start, end


def _has_conflict_with_door(
    candidate: WindowCandidate,
    door: OpeningPayload,
    clearance: float,
    tolerance: float,
) -> bool:
    if door["room_name"] != candidate["room_name"]:
        return False

    if door["side"] != candidate["side"]:
        return False

    cand_start, cand_end = _get_axis_interval(candidate["side"], candidate)
    door_start, door_end = _get_axis_interval(candidate["side"], door)

    # Hard reject if overlap or if nearest gap is below required clearance.
    if cand_start <= door_end + tolerance and door_start <= cand_end + tolerance:
        return True

    gap = min(abs(cand_start - door_end), abs(door_start - cand_end))
    return gap + tolerance < clearance


def build_window_candidates_for_room(
    room: NormalizedRoom,
    exterior_sides: set[str],
    existing_openings: list[OpeningPayload],
    window_width: float,
    door_clearance: float,
    tolerance: float = GEOMETRIC_TOLERANCE,
) -> list[WindowCandidate]:
    candidates: list[WindowCandidate] = []
    side_order: tuple[str, ...] = CARDINAL_SIDES

    for side in side_order:
        if side not in exterior_sides:
            continue

        if side in ("south", "north"):
            span_start = room["x"]
            span_end = room["x_end"]
            span_length = span_end - span_start
            if span_length + tolerance < window_width:
                continue

            x1 = span_start + ((span_length - window_width) / 2.0)
            x2 = x1 + window_width
            y = room["y"] if side == "south" else room["y_end"]
            candidate: WindowCandidate = {
                "room_name": room["name"],
                "room_type": room["type"],
                "side": side,
                "x1": x1,
                "y1": y,
                "x2": x2,
                "y2": y,
            }
        else:
            span_start = room["y"]
            span_end = room["y_end"]
            span_length = span_end - span_start
            if span_length + tolerance < window_width:
                continue

            y1 = span_start + ((span_length - window_width) / 2.0)
            y2 = y1 + window_width
            x = room["x"] if side == "west" else room["x_end"]
            candidate = {
                "room_name": room["name"],
                "room_type": room["type"],
                "side": side,
                "x1": x,
                "y1": y1,
                "x2": x,
                "y2": y2,
            }

        has_conflict = any(
            _has_conflict_with_door(candidate, opening, door_clearance, tolerance)
            for opening in existing_openings
            if opening["opening_type"] in ("mainDoor", "internalDoor")
        )
        if not has_conflict:
            candidates.append(candidate)

    return candidates


def add_windows_placement_constraint(
    model: cp_model.CpModel,
    candidates: list[WindowCandidate],
) -> WindowDecisionVars:
    """Select exactly one window candidate for each room with feasible options."""
    selected_vars: list[cp_model.IntVar] = []
    room_to_indices: defaultdict[str, list[int]] = defaultdict(list)

    for index, candidate in enumerate(candidates):
        selected = model.NewBoolVar(f"window_selected_{index}")  # type: ignore
        selected_vars.append(selected)
        room_to_indices[candidate["room_name"]].append(index)

    for indices in room_to_indices.values():
        model.Add(sum(selected_vars[i] for i in indices) == 1)

    return {"selected": selected_vars}

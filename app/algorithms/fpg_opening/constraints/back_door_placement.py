from __future__ import annotations

from ortools.sat.python import cp_model

from app.algorithms.types import NormalizedRoom
from app.algorithms.types.solvers import BackDoorCandidate, BackDoorDecisionVars
from app.algorithms.fpg_opening.utils import get_exterior_sides
from app.core.fpg_opening_config import (
    BACK_DOOR_ELIGIBLE_ROOM_TYPES,
    BACK_DOOR_ROOM_TYPE_PRIORITY,
    GEOMETRIC_TOLERANCE,
    normalize_room_type,
)


def _is_eligible_room_type(room_type: str) -> bool:
    normalized = normalize_room_type(room_type)
    return normalized in BACK_DOOR_ELIGIBLE_ROOM_TYPES


def _room_type_priority(room_type: str) -> int:
    normalized = normalize_room_type(room_type)
    return BACK_DOOR_ROOM_TYPE_PRIORITY.get(normalized, 999)


def _build_horizontal_back_candidates(
    all_rooms: list[NormalizedRoom],
    preferred_door_length: float,
    tolerance: float,
) -> list[BackDoorCandidate]:
    candidates: list[BackDoorCandidate] = []

    for room in all_rooms:
        if not _is_eligible_room_type(room["type"]):
            continue

        exterior_sides = get_exterior_sides(
            target_room=room,
            all_rooms=all_rooms,
            tolerance=tolerance,
        )
        if "north" not in exterior_sides:
            continue

        width = room["x_end"] - room["x"]
        if width <= tolerance:
            continue

        door_length = min(preferred_door_length, width)
        mid_x = (room["x"] + room["x_end"]) / 2.0
        x1 = mid_x - (door_length / 2.0)
        x2 = mid_x + (door_length / 2.0)

        candidates.append(
            {
                "room_name": room["name"],
                "room_type": room["type"],
                "side": "north",
                "x1": x1,
                "y1": room["y_end"],
                "x2": x2,
                "y2": room["y_end"],
            }
        )

    if not candidates:
        return []

    furthest_back_y = max(candidate["y1"] for candidate in candidates)
    shortlisted = [
        candidate
        for candidate in candidates
        if abs(candidate["y1"] - furthest_back_y) <= tolerance
    ]
    shortlisted.sort(
        key=lambda candidate: (
            _room_type_priority(candidate["room_type"]),
            candidate["room_name"],
        )
    )
    return shortlisted


def _build_vertical_outermost_candidates(
    all_rooms: list[NormalizedRoom],
    preferred_door_length: float,
    tolerance: float,
) -> list[BackDoorCandidate]:
    west_candidates: list[BackDoorCandidate] = []
    east_candidates: list[BackDoorCandidate] = []

    for room in all_rooms:
        if not _is_eligible_room_type(room["type"]):
            continue

        exterior_sides = get_exterior_sides(
            target_room=room,
            all_rooms=all_rooms,
            tolerance=tolerance,
        )

        height = room["y_end"] - room["y"]
        if height <= tolerance:
            continue

        door_length = min(preferred_door_length, height)
        mid_y = (room["y"] + room["y_end"]) / 2.0
        y1 = mid_y - (door_length / 2.0)
        y2 = mid_y + (door_length / 2.0)

        if "west" in exterior_sides:
            west_candidates.append(
                {
                    "room_name": room["name"],
                    "room_type": room["type"],
                    "side": "west",
                    "x1": room["x"],
                    "y1": y1,
                    "x2": room["x"],
                    "y2": y2,
                }
            )

        if "east" in exterior_sides:
            east_candidates.append(
                {
                    "room_name": room["name"],
                    "room_type": room["type"],
                    "side": "east",
                    "x1": room["x_end"],
                    "y1": y1,
                    "x2": room["x_end"],
                    "y2": y2,
                }
            )

    shortlisted: list[BackDoorCandidate] = []

    if west_candidates:
        leftmost_x = min(candidate["x1"] for candidate in west_candidates)
        shortlisted.extend(
            [
                candidate
                for candidate in west_candidates
                if abs(candidate["x1"] - leftmost_x) <= tolerance
            ]
        )

    if east_candidates:
        rightmost_x = max(candidate["x1"] for candidate in east_candidates)
        shortlisted.extend(
            [
                candidate
                for candidate in east_candidates
                if abs(candidate["x1"] - rightmost_x) <= tolerance
            ]
        )

    shortlisted.sort(
        key=lambda candidate: (
            _room_type_priority(candidate["room_type"]),
            candidate["room_name"],
            0 if candidate["side"] == "west" else 1,
        )
    )
    return shortlisted


def build_back_door_candidates(
    all_rooms: list[NormalizedRoom],
    preferred_door_length: float,
    tolerance: float = GEOMETRIC_TOLERANCE,
) -> list[BackDoorCandidate]:
    """Build ranked back-door candidates from kitchen/hallway exterior walls.

    Priority order:
    1) Furthest-back horizontal exterior wall segments (north side).
    2) Fallback to outer-most exterior vertical segments (west/east).
    3) Fallback to any available exterior segments if preferred options are too constrained.
    """
    horizontal_candidates = _build_horizontal_back_candidates(
        all_rooms=all_rooms,
        preferred_door_length=preferred_door_length,
        tolerance=tolerance,
    )
    if horizontal_candidates:
        return horizontal_candidates

    vertical_candidates = _build_vertical_outermost_candidates(
        all_rooms=all_rooms,
        preferred_door_length=preferred_door_length,
        tolerance=tolerance,
    )
    if vertical_candidates:
        return vertical_candidates

    # Final fallback: try any exterior wall segment on kitchen or hallway.
    all_fallback_candidates: list[BackDoorCandidate] = []
    for room in all_rooms:
        if not _is_eligible_room_type(room["type"]):
            continue

        exterior_sides = get_exterior_sides(
            target_room=room,
            all_rooms=all_rooms,
            tolerance=tolerance,
        )
        if not exterior_sides:
            continue

        for side in exterior_sides:
            if side in ("south", "north"):
                span_start = room["x"]
                span_end = room["x_end"]
            else:
                span_start = room["y"]
                span_end = room["y_end"]

            span_length = span_end - span_start
            if span_length <= tolerance:
                continue

            door_length = min(preferred_door_length, span_length)
            mid = (span_start + span_end) / 2.0
            coord1 = mid - (door_length / 2.0)
            coord2 = mid + (door_length / 2.0)

            if side in ("south", "north"):
                candidate: BackDoorCandidate = {
                    "room_name": room["name"],
                    "room_type": room["type"],
                    "side": side,
                    "x1": coord1,
                    "y1": room["y"] if side == "south" else room["y_end"],
                    "x2": coord2,
                    "y2": room["y"] if side == "south" else room["y_end"],
                }
            else:
                candidate = {
                    "room_name": room["name"],
                    "room_type": room["type"],
                    "side": side,
                    "x1": room["x"] if side == "west" else room["x_end"],
                    "y1": coord1,
                    "x2": room["x"] if side == "west" else room["x_end"],
                    "y2": coord2,
                }

            all_fallback_candidates.append(candidate)

    if all_fallback_candidates:
        all_fallback_candidates.sort(
            key=lambda c: (
                _room_type_priority(c["room_type"]),
                c["room_name"],
                0
                if c["side"] in ("south", "north")
                else (1 if c["side"] == "west" else 2),
            )
        )
        return all_fallback_candidates

    return []


def add_back_door_placement_constraint(
    model: cp_model.CpModel,
    candidates: list[BackDoorCandidate],
) -> BackDoorDecisionVars:
    """Select exactly one back-door candidate when candidate list is non-empty."""
    selected_vars: list[cp_model.IntVar] = [
        model.NewBoolVar(f"back_door_selected_{index}")  # type: ignore
        for index, _ in enumerate(candidates)
    ]

    if not selected_vars:
        return {"selected": selected_vars}

    model.Add(sum(selected_vars) == 1)

    if len(selected_vars) > 1:
        model.Minimize(
            cp_model.LinearExpr.Sum(
                [index * selected for index, selected in enumerate(selected_vars)]
            )
        )

    return {"selected": selected_vars}

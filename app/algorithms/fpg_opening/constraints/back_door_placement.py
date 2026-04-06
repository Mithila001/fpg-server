from __future__ import annotations

from ortools.sat.python import cp_model

from app.algorithms.fpg_opening.types.opening import NormalizedRoom
from app.algorithms.fpg_opening.types.opening_solver import BackDoorCandidate, BackDoorDecisionVars
from app.algorithms.fpg_opening.utils import get_exterior_sides


def _normalize_room_type(room_type: str) -> str:
    return room_type.strip().lower()


def _is_eligible_room_type(room_type: str) -> bool:
    normalized = _normalize_room_type(room_type)
    return normalized in {"kitchen", "hallway"}


def _room_type_priority(room_type: str) -> int:
    normalized = _normalize_room_type(room_type)
    if normalized == "kitchen":
        return 0
    return 1


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
    tolerance: float = 1e-6,
) -> list[BackDoorCandidate]:
    """Build ranked back-door candidates from kitchen/hallway exterior walls.

    Priority order:
    1) Furthest-back horizontal exterior wall segments (north side).
    2) Fallback to outer-most exterior vertical segments (west/east).
    """
    horizontal_candidates = _build_horizontal_back_candidates(
        all_rooms=all_rooms,
        preferred_door_length=preferred_door_length,
        tolerance=tolerance,
    )
    if horizontal_candidates:
        return horizontal_candidates

    return _build_vertical_outermost_candidates(
        all_rooms=all_rooms,
        preferred_door_length=preferred_door_length,
        tolerance=tolerance,
    )


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
            cp_model.LinearExpr.Sum([
                index * selected for index, selected in enumerate(selected_vars)
            ])
        )

    return {"selected": selected_vars}
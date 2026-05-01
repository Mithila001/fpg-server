from __future__ import annotations
from typing import Any
from app.algorithms.types import FpgRequirements

from ..util.scoring_common import (
    ROOM_TYPE_GARAGE,
    ROOM_TYPE_HALLWAY,
    ROOM_TYPE_KITCHEN,
    ROOM_TYPE_VERANDA,
    OptunaScorePoint,
    SectionScore,
    normalize_section_score,
    room_type_counts,
)

# --- DEBUG CONTROL ---
DEBUG_VERBOSE = False  # Set to False to silence debug prints
# ---------------------

# Change this value to automatically scale the entire section's scoring
OUTER_CLEARANCE_MAX_SCORE = 20

# Dynamically calculate weights based on the max score.
# The total score is divided into 3 equal parts for Veranda, Garage, and Service.
_BASE_WEIGHT = OUTER_CLEARANCE_MAX_SCORE / 3.0

CLEARANCE_TYPE_WEIGHTS: dict[str, float] = {
    ROOM_TYPE_VERANDA: _BASE_WEIGHT,
    ROOM_TYPE_GARAGE: _BASE_WEIGHT,
}

SERVICE_CLEARANCE_WEIGHT = _BASE_WEIGHT
HALLWAY_SCORE_FACTOR = 0.7  # Awards 70% of the SERVICE_CLEARANCE_WEIGHT if hallway is used instead of kitchen


def _clearance_box(x: float, y: float, side: str) -> tuple[float, float, float, float]:
    if side == "back":
        return x - 10.0, y, x + 10.0, y + 20.0
    if side == "front":
        return x - 10.0, y - 20.0, x + 10.0, y
    if side == "left":
        return x - 20.0, y - 10.0, x, y + 10.0
    if side == "right":
        return x, y - 10.0, x + 20.0, y + 10.0
    raise ValueError(f"Unsupported clearance side: {side}")


def _box_is_clear(
    room: OptunaScorePoint, side: str, room_points: list[OptunaScorePoint]
) -> tuple[bool, list[str]]:
    min_x, min_y, max_x, max_y = _clearance_box(room.x, room.y, side)
    blockers = [
        other.name
        for other in room_points
        if other.name != room.name
        and min_x <= other.x <= max_x
        and min_y <= other.y <= max_y
    ]
    return len(blockers) == 0, blockers


def score_outer_clearance(
    requirements: FpgRequirements, room_points: list[OptunaScorePoint]
) -> SectionScore:
    required_room_types = {req.type for req in requirements.rooms}
    print("\n--- Scoring Outer Clearance ---\n")

    # 1. Dynamic Max Calculation
    dynamic_max_score = sum(
        w for t, w in CLEARANCE_TYPE_WEIGHTS.items() if t in required_room_types
    )
    has_service_req = (
        ROOM_TYPE_KITCHEN in required_room_types
        or ROOM_TYPE_HALLWAY in required_room_types
    )
    if has_service_req:
        dynamic_max_score += SERVICE_CLEARANCE_WEIGHT

    if dynamic_max_score <= 0:
        return SectionScore(
            score=0.0,
            max_score=0.0,
            details={"note": "No clearance rooms"},
            warnings=[],
        )

    raw_score = 0.0
    lost_points_report = []
    room_details: dict[str, Any] = {}
    counts = room_type_counts(room_points)

    # 2. Independent Rooms
    for room in room_points:
        if room.room_type in CLEARANCE_TYPE_WEIGHTS:
            alloc = max(1, int(counts.get(room.room_type, 1)))
            weight = CLEARANCE_TYPE_WEIGHTS[room.room_type] / alloc
            passed, blockers = _box_is_clear(room, "front", room_points)

            val = weight if passed else 0.0
            raw_score += val
            if not passed:
                lost_points_report.append(
                    f"[-] {room.name} ({room.room_type}): -{weight:.2f} pts. Blocked by: {blockers}"
                )

            room_details[room.name] = {
                "type": room.room_type,
                "passed": passed,
                "awarded": val,
            }

    # 3. Priority Service Clearance
    service_awarded = 0.0
    kitchens = [r for r in room_points if r.room_type == ROOM_TYPE_KITCHEN]
    hallways = [r for r in room_points if r.room_type == ROOM_TYPE_HALLWAY]

    # Try Kitchen first
    k_passed = False
    for k in kitchens:
        passed, blockers = _box_is_clear(k, "back", room_points)
        if passed:
            service_awarded = SERVICE_CLEARANCE_WEIGHT
            k_passed = True
            room_details[k.name] = {
                "type": "KITCHEN",
                "passed": True,
                "awarded": service_awarded,
            }
            break
        room_details[k.name] = {
            "type": "KITCHEN",
            "passed": False,
            "blockers": blockers,
        }

    # Fallback to Hallway if Kitchen failed
    if not k_passed:
        h_passed = False
        for h in hallways:
            passed, blockers = _box_is_clear(h, "back", room_points)
            if passed:
                service_awarded = SERVICE_CLEARANCE_WEIGHT * HALLWAY_SCORE_FACTOR
                h_passed = True
                room_details[h.name] = {
                    "type": "HALLWAY",
                    "passed": True,
                    "awarded": service_awarded,
                }
                lost_points_report.append(
                    f"[-] Service: -{SERVICE_CLEARANCE_WEIGHT - service_awarded:.2f} pts. Kitchen blocked, using Hallway instead."
                )
                break
            room_details[h.name] = {
                "type": "HALLWAY",
                "passed": False,
                "blockers": blockers,
            }

        if not h_passed and has_service_req:
            lost_points_report.append(
                f"[-] Service: -{SERVICE_CLEARANCE_WEIGHT:.2f} pts. Both Kitchen and Hallway are blocked."
            )

    raw_score += service_awarded

    # --- DEBUG PRINT ---
    if DEBUG_VERBOSE:
        print(
            f"\n--- CLEARANCE DEBUG (Total: {raw_score:.2f}/{dynamic_max_score:.2f}) ---"
        )
        if not lost_points_report:
            print("[+] Perfect Score!")
        for entry in lost_points_report:
            print(entry)
        print("-------------------------------------------\n")

    return SectionScore(
        score=normalize_section_score(raw_score, dynamic_max_score),
        max_score=dynamic_max_score,
        details={"rooms": room_details},
        warnings=[],
    )

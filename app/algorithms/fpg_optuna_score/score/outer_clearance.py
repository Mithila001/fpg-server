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

OUTER_CLEARANCE_MAX_SCORE = 20.0

CLEARANCE_TYPE_WEIGHTS: dict[str, float] = {
    ROOM_TYPE_VERANDA: 5.0,
    ROOM_TYPE_GARAGE: 5.0,
    ROOM_TYPE_KITCHEN: 5.0,
    ROOM_TYPE_HALLWAY: 5.0,
}


def _clearance_box(
    x: float,
    y: float,
    side: str,
) -> tuple[float, float, float, float]:
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
    room: OptunaScorePoint,
    side: str,
    room_points: list[OptunaScorePoint],
) -> tuple[bool, list[str]]:
    min_x, min_y, max_x, max_y = _clearance_box(room.x, room.y, side)
    blockers: list[str] = []

    for other in room_points:
        if other.name == room.name:
            continue
        if min_x <= other.x <= max_x and min_y <= other.y <= max_y:
            blockers.append(other.name)

    return len(blockers) == 0, blockers


def _evaluate_room_clearance(
    room: OptunaScorePoint,
    room_points: list[OptunaScorePoint],
) -> tuple[bool, dict[str, Any]]:
    if room.room_type == ROOM_TYPE_VERANDA:
        passed, blockers = _box_is_clear(room, "front", room_points)
        return passed, {"side": "front", "blockers": blockers}
    if room.room_type == ROOM_TYPE_GARAGE:
        passed, blockers = _box_is_clear(room, "front", room_points)
        return passed, {"side": "front", "blockers": blockers}
    if room.room_type == ROOM_TYPE_KITCHEN:
        results: dict[str, Any] = {}
        for side in ("back", "left", "right"):
            passed, blockers = _box_is_clear(room, side, room_points)
            results[side] = {"passed": passed, "blockers": blockers}
        passed = any(item["passed"] for item in results.values())
        return passed, results
    if room.room_type == ROOM_TYPE_HALLWAY:
        passed, blockers = _box_is_clear(room, "back", room_points)
        return passed, {"side": "back", "blockers": blockers}
    return False, {"reason": "room type is not clearance-scored"}


def score_outer_clearance(
    requirements: FpgRequirements,
    room_points: list[OptunaScorePoint],
) -> SectionScore:
    _ = requirements
    counts = room_type_counts(room_points)
    raw_score = 0.0
    room_details: dict[str, Any] = {}
    warnings: list[str] = []

    for room in room_points:
        if room.room_type not in CLEARANCE_TYPE_WEIGHTS:
            continue

        allocation_count = max(1, int(counts.get(room.room_type, 1)))
        room_weight = CLEARANCE_TYPE_WEIGHTS[room.room_type] / allocation_count
        passed, detail = _evaluate_room_clearance(room, room_points)
        awarded = room_weight if passed else 0.0
        raw_score += awarded
        room_details[room.name] = {
            "type": room.room_type,
            "passed": passed,
            "weight": room_weight,
            "awarded": awarded,
            "detail": detail,
        }

    normalized = normalize_section_score(raw_score, OUTER_CLEARANCE_MAX_SCORE)
    if normalized != raw_score:
        warnings.append(
            f"Outer clearance score normalized from {raw_score:.2f} to {normalized:.2f}"
        )

    return SectionScore(
        score=normalized,
        max_score=OUTER_CLEARANCE_MAX_SCORE,
        details={"rooms": room_details},
        warnings=warnings,
    )
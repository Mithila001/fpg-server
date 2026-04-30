from __future__ import annotations

from typing import Any

from app.algorithms.types import FpgRequirements

from ..util.scoring_common import (
    ROOM_TYPE_BATHROOM,
    ROOM_TYPE_GARAGE,
    ROOM_TYPE_HALLWAY,
    ROOM_TYPE_KITCHEN,
    ROOM_TYPE_LIVING_ROOM,
    ROOM_TYPE_VERANDA,
    OptunaScorePoint,
    SectionScore,
    normalize_section_score,
    point_to_cell,
    room_type_counts,
)

FLOOR_PLAN_ZONE_MAX_SCORE = 30.0

# Hardcoded weights are intentionally centralized for quick tuning.
ZONE_TYPE_WEIGHTS: dict[str, float] = {
    ROOM_TYPE_VERANDA: 5.0,
    ROOM_TYPE_GARAGE: 5.0,
    ROOM_TYPE_KITCHEN: 7.0,
    ROOM_TYPE_HALLWAY: 4.0,
    ROOM_TYPE_LIVING_ROOM: 5.0,
    ROOM_TYPE_BATHROOM: 4.0,
}

BOTTOM_ROW_ZONES = {(1, 1), (2, 1), (3, 1)}
GARAGE_ZONES = {(1, 1), (3, 1)}
KITCHEN_ZONE = (2, 2)
LIVING_ROOM_ZONES = {(1, 1), (2, 1), (3, 1), (1, 2), (2, 2), (3, 2)}
BATHROOM_ZONES = {(2, 2)}


def _zone_name(cell_x: int, cell_y: int) -> str:
    return f"({cell_x}, {cell_y})"


def _evaluate_zone_rule(room: OptunaScorePoint, cell: tuple[int, int]) -> tuple[bool, str]:
    if room.room_type == ROOM_TYPE_VERANDA:
        passed = cell in BOTTOM_ROW_ZONES
        return passed, "veranda must be in bottom row"
    if room.room_type == ROOM_TYPE_GARAGE:
        passed = cell in GARAGE_ZONES
        return passed, "garage must be in bottom corners"
    if room.room_type == ROOM_TYPE_KITCHEN:
        passed = cell == KITCHEN_ZONE
        return passed, "kitchen must be in center-middle zone"
    if room.room_type == ROOM_TYPE_HALLWAY:
        passed = cell not in BOTTOM_ROW_ZONES
        return passed, "hallway must avoid bottom row"
    if room.room_type == ROOM_TYPE_LIVING_ROOM:
        passed = cell in LIVING_ROOM_ZONES
        return passed, "living room should stay in the lower two rows"
    if room.room_type == ROOM_TYPE_BATHROOM:
        passed = cell in BATHROOM_ZONES
        return passed, "bathroom should stay in zone (2, 2)"
    return False, "room type is not zone-scored"


def score_floor_plan_zones(
    requirements: FpgRequirements,
    room_points: list[OptunaScorePoint],
) -> SectionScore:
    cfg = requirements.config
    floor_width = float(cfg.floor_plan_width)
    floor_height = float(cfg.floor_plan_height)
    counts = room_type_counts(room_points)

    scored_room_details: dict[str, Any] = {}
    raw_score = 0.0
    warnings: list[str] = []

    for room in room_points:
        if room.room_type not in ZONE_TYPE_WEIGHTS:
            continue

        cell = point_to_cell(room.x, room.y, floor_width, floor_height)
        allocation_count = max(1, int(counts.get(room.room_type, 1)))
        room_weight = ZONE_TYPE_WEIGHTS[room.room_type] / allocation_count
        passed, reason = _evaluate_zone_rule(room, cell)
        awarded = room_weight if passed else 0.0
        raw_score += awarded

        scored_room_details[room.name] = {
            "type": room.room_type,
            "zone": _zone_name(*cell),
            "passed": passed,
            "reason": reason,
            "weight": room_weight,
            "awarded": awarded,
        }

    normalized = normalize_section_score(raw_score, FLOOR_PLAN_ZONE_MAX_SCORE)
    if normalized != raw_score:
        warnings.append(
            f"Zone score normalized from {raw_score:.2f} to {normalized:.2f}"
        )

    return SectionScore(
        score=normalized,
        max_score=FLOOR_PLAN_ZONE_MAX_SCORE,
        details={"rooms": scored_room_details, "counts": dict(counts)},
        warnings=warnings,
    )
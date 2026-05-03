from __future__ import annotations

from typing import Any

from app.algorithms.types import FpgRequirements
from app.core.fpg_rooms.config_fpg import OPTUNA_SCORING_VALUES

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

# Zone-scored room types (previously weighted individually).
ZONE_SCORABLE_TYPES = {
    ROOM_TYPE_VERANDA,
    ROOM_TYPE_GARAGE,
    ROOM_TYPE_KITCHEN,
    ROOM_TYPE_HALLWAY,
    ROOM_TYPE_LIVING_ROOM,
    ROOM_TYPE_BATHROOM,
}

BOTTOM_ROW_ZONES = {(1, 1), (2, 1), (3, 1)}
GARAGE_ZONES = {(1, 1), (3, 1)}
NO_KITCHEN_ZONE = (2, 2)
LIVING_ROOM_ZONES = {(1, 1), (2, 1), (3, 1), (1, 2), (2, 2), (3, 2)}
NO_BATHROOM_ZONES = {(2, 2)}


def _zone_name(cell_x: int, cell_y: int) -> str:
    return f"({cell_x}, {cell_y})"


def _evaluate_zone_rule(
    room: OptunaScorePoint, cell: tuple[int, int]
) -> tuple[bool, str]:
    if room.room_type == ROOM_TYPE_VERANDA:
        passed = cell in BOTTOM_ROW_ZONES
        return passed, "veranda must be in bottom row"
    if room.room_type == ROOM_TYPE_GARAGE:
        passed = cell in GARAGE_ZONES
        return passed, "garage must be in bottom corners"
    if room.room_type == ROOM_TYPE_KITCHEN:
        passed = cell not in NO_KITCHEN_ZONE
        return passed, "kitchen must not be in center-middle zone"
    if room.room_type == ROOM_TYPE_HALLWAY:
        passed = cell not in BOTTOM_ROW_ZONES
        return passed, "hallway must avoid bottom row"
    if room.room_type == ROOM_TYPE_LIVING_ROOM:
        passed = cell in LIVING_ROOM_ZONES
        return passed, "living room should stay in the lower two rows"
    if room.room_type == ROOM_TYPE_BATHROOM:
        passed = cell not in NO_BATHROOM_ZONES
        return passed, "bathroom should not stay in zone (2, 2)"
    return False, "room type is not zone-scored"


def score_floor_plan_zones(
    requirements: FpgRequirements,
    room_points: list[OptunaScorePoint],
) -> SectionScore:
    cfg = requirements.config
    floor_width = float(cfg.floor_plan_width)
    floor_height = float(cfg.floor_plan_height)
    counts = room_type_counts(room_points)

    # Use optuna-configured max for zone scoring
    optuna_max = float(OPTUNA_SCORING_VALUES.get("optuna_score_zone", 0.0))

    scored_room_details: dict[str, Any] = {}
    warnings: list[str] = []

    # First pass: collect per-room pass/fail and count scorable rooms
    scorable_total = 0
    passed_count = 0

    for room in room_points:
        if room.room_type not in ZONE_SCORABLE_TYPES:
            continue

        scorable_total += 1
        cell = point_to_cell(room.x, room.y, floor_width, floor_height)
        passed, reason = _evaluate_zone_rule(room, cell)

        if passed:
            passed_count += 1

        if not passed:
            print(
                f"[score_floor_plan_zones] Room '{room.name}' failed: {reason} "
                f"(Current zone: {_zone_name(*cell)})"
            )

        scored_room_details[room.name] = {
            "type": room.room_type,
            "zone": _zone_name(*cell),
            "passed": passed,
            "reason": reason,
        }

    if scorable_total == 0:
        warnings.append("No scorable rooms found for zone scoring")
        return SectionScore(
            score=0.0,
            max_score=optuna_max,
            details={"rooms": scored_room_details, "counts": dict(counts)},
            warnings=warnings,
        )

    # Distribute optuna_max evenly across scorable rooms and award per passed room
    per_room_award = (
        float(optuna_max) / float(scorable_total) if optuna_max > 0 else 0.0
    )
    raw_score = per_room_award * float(passed_count)

    normalized = normalize_section_score(raw_score, optuna_max)

    # Attach awarded values to details for clarity
    for name, info in scored_room_details.items():
        if info["type"] in ZONE_SCORABLE_TYPES and info.get("passed"):
            info["awarded"] = per_room_award
        else:
            info["awarded"] = 0.0

    if normalized != raw_score:
        warnings.append(
            f"Zone score normalized from {raw_score:.2f} to {normalized:.2f} "
            f"(Max possible: {optuna_max:.2f})"
        )

    return SectionScore(
        score=normalized,
        max_score=optuna_max,
        details={
            "rooms": scored_room_details,
            "counts": dict(counts),
            "scorable_total": scorable_total,
            "passed": passed_count,
        },
        warnings=warnings,
    )

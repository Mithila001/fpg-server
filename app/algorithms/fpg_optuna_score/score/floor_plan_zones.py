from __future__ import annotations

import math
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

# Zone-scored room types
ZONE_SCORABLE_TYPES = {
    ROOM_TYPE_VERANDA,
    ROOM_TYPE_GARAGE,
    ROOM_TYPE_KITCHEN,
    ROOM_TYPE_HALLWAY,
    ROOM_TYPE_LIVING_ROOM,
    ROOM_TYPE_BATHROOM,
}

# Original zone rules mapped to sets of valid (x, y) grid coordinates.
# Assuming a 3x3 grid system standard to this algorithm.
ALL_ZONES = {(x, y) for x in range(1, 4) for y in range(1, 4)}

BOTTOM_ROW_ZONES = {(1, 1), (2, 1), (3, 1)}
GARAGE_ZONES = {(1, 1), (3, 1)}
NO_KITCHEN_ZONE = (2, 2)
LIVING_ROOM_ZONES = {(1, 1), (2, 1), (3, 1), (1, 2), (2, 2), (3, 2)}
NO_BATHROOM_ZONES = {(2, 2)}

# Map each room type to its exact set of valid grid cells
VALID_ZONES_BY_TYPE = {
    ROOM_TYPE_VERANDA: BOTTOM_ROW_ZONES,
    ROOM_TYPE_GARAGE: GARAGE_ZONES,
    ROOM_TYPE_KITCHEN: ALL_ZONES - {NO_KITCHEN_ZONE},
    ROOM_TYPE_HALLWAY: ALL_ZONES - BOTTOM_ROW_ZONES,
    ROOM_TYPE_LIVING_ROOM: LIVING_ROOM_ZONES,
    ROOM_TYPE_BATHROOM: ALL_ZONES - NO_BATHROOM_ZONES,
}

# The multiplier controls how fast the score falls to 0.
# A multiplier of 1.5 means a room placed ~0.66 across the house from its target zone scores 0.
FALLOFF_MULTIPLIER = 1.5


def _zone_name(cell_x: int, cell_y: int) -> str:
    return f"({cell_x}, {cell_y})"


def _calculate_min_distance(nx: float, ny: float, valid_cells: set[tuple[int, int]]) -> float:
    """
    Calculates the shortest Euclidean distance from a normalized point (nx, ny)
    to the closest valid cell bounding box.
    """
    min_dist = float('inf')
    
    for cx, cy in valid_cells:
        # Calculate cell bounding box in normalized 0.0 to 1.0 space (3x3 grid)
        xmin = (cx - 1) / 3.0
        xmax = cx / 3.0
        ymin = (cy - 1) / 3.0
        ymax = cy / 3.0

        # Distance to the bounding box (0 if inside the box)
        dx = max(0.0, xmin - nx, nx - xmax)
        dy = max(0.0, ymin - ny, ny - ymax)
        
        dist = math.sqrt(dx * dx + dy * dy)
        
        if dist < min_dist:
            min_dist = dist

    return min_dist


def _evaluate_zone_score_continuous(
    room: OptunaScorePoint, nx: float, ny: float
) -> tuple[float, float, str]:
    """
    Returns (score_out_of_100, shortest_distance, reason).
    """
    if room.room_type not in VALID_ZONES_BY_TYPE:
        return 0.0, 0.0, "room type is not zone-scored"

    valid_cells = VALID_ZONES_BY_TYPE[room.room_type]
    dist = _calculate_min_distance(nx, ny, valid_cells)

    if dist == 0.0:
        return 100.0, dist, "perfectly within target zone"

    # Soft falloff linearly scales the distance down to 0
    raw_score = 100.0 * (1.0 - (dist * FALLOFF_MULTIPLIER))
    score = max(0.0, raw_score)

    return score, dist, f"out of zone by {dist:.3f} normalized distance"


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

    scorable_total = 0
    total_score_out_of_100 = 0.0

    for room in room_points:
        if room.room_type not in ZONE_SCORABLE_TYPES:
            continue

        scorable_total += 1
        
        # Protect against division by zero errors
        nx = room.x / floor_width if floor_width > 0 else 0.5
        ny = room.y / floor_height if floor_height > 0 else 0.5
        
        # Calculate 0-100 continuous score
        score_100, dist, reason = _evaluate_zone_score_continuous(room, nx, ny)
        total_score_out_of_100 += score_100

        # Optional: track the old discrete cell just for logging context
        cell = point_to_cell(room.x, room.y, floor_width, floor_height)

        if score_100 < 100.0:
            print(
                f"[score_floor_plan_zones] Room '{room.name}' penalized: {reason}. "
                f"Score: {score_100:.2f}/100 (Current discrete zone: {_zone_name(*cell)})"
            )

        scored_room_details[room.name] = {
            "type": room.room_type,
            "zone": _zone_name(*cell),
            "normalized_pos": (round(nx, 3), round(ny, 3)),
            "distance_to_target": round(dist, 3),
            "score_100": round(score_100, 2),
            "reason": reason,
        }

    if scorable_total == 0:
        warnings.append("No scorable rooms found for zone scoring. Defaulting to full score.")
        return SectionScore(
            score=optuna_max,
            max_score=optuna_max,
            details={"rooms": scored_room_details, "counts": dict(counts)},
            warnings=warnings,
        )

    # Max possible raw score is if every room got 100
    max_possible_raw_score = float(scorable_total) * 100.0
    
    # Map the accumulated 0-100 score proportionally onto the target optuna_max limit
    raw_ratio = total_score_out_of_100 / max_possible_raw_score if max_possible_raw_score > 0 else 0.0
    raw_optuna_score = raw_ratio * optuna_max
    
    normalized = normalize_section_score(raw_optuna_score, optuna_max)

    # Attach equivalent awarded values mapped back to Optuna scales for detail clarity
    for name, info in scored_room_details.items():
        if info["type"] in ZONE_SCORABLE_TYPES:
            # How much this specific room contributed toward the absolute optuna_max pool
            contribution = (info["score_100"] / 100.0) * (optuna_max / scorable_total)
            info["awarded"] = round(contribution, 3)
        else:
            info["awarded"] = 0.0

    if normalized != raw_optuna_score:
        warnings.append(
            f"Zone score normalized from {raw_optuna_score:.2f} to {normalized:.2f} "
            f"(Max possible: {optuna_max:.2f})"
        )

    return SectionScore(
        score=normalized,
        max_score=optuna_max,
        details={
            "rooms": scored_room_details,
            "counts": dict(counts),
            "scorable_total": scorable_total,
            "total_score_100": round(total_score_out_of_100, 2),
        },
        warnings=warnings,
    )
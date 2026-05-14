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
)

from app.core.fpg_rooms.config_fpg import OPTUNA_SCORING_VALUES

# --- DEBUG CONTROL ---
DEBUG_VERBOSE = False  # Set to False to silence debug prints
# ---------------------

# --- SCORING CONSTANTS ---
PENALTY_PER_BLOCK = -10.0  # Penalty applied per blocking room in the clearance zone
# -------------------------


def _clearance_box(x: float, y: float, side: str) -> tuple[float, float, float, float]:
    """Helper to determine the bounding box for clearance checks."""
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
    """Helper to check if a specific side of a room is clear of other rooms."""
    min_x, min_y, max_x, max_y = _clearance_box(room.x, room.y, side)
    blockers = [
        other.name
        for other in room_points
        if other.name != room.name
        and min_x <= other.x <= max_x
        and min_y <= other.y <= max_y
    ]
    return len(blockers) == 0, blockers


def _evaluate_veranda(room_points: list[OptunaScorePoint]) -> tuple[float, bool]:
    """Evaluates Veranda clearance. Returns (score_out_of_100, is_evaluated)"""
    verandas = [r for r in room_points if r.room_type == ROOM_TYPE_VERANDA]

    # Guard rail: Safety Gate to not damage the scoring if room doesn't exist
    if not verandas:
        return 0.0, False

    total_score = 0.0
    for v in verandas:
        _, blockers = _box_is_clear(v, "front", room_points)
        # Apply penalty per blocker, ensure score doesn't drop below 0
        score = max(0.0, 100.0 + (len(blockers) * PENALTY_PER_BLOCK))
        total_score += score

    # Average score if there are multiple verandas
    return total_score / len(verandas), True


def _evaluate_garage(room_points: list[OptunaScorePoint]) -> tuple[float, bool]:
    """Evaluates Garage clearance. Returns (score_out_of_100, is_evaluated)"""
    garages = [r for r in room_points if r.room_type == ROOM_TYPE_GARAGE]

    # Guard rail: Safety Gate to not damage the scoring if room doesn't exist
    if not garages:
        return 0.0, False

    total_score = 0.0
    for g in garages:
        _, blockers = _box_is_clear(g, "front", room_points)
        # Apply penalty per blocker, ensure score doesn't drop below 0
        score = max(0.0, 100.0 + (len(blockers) * PENALTY_PER_BLOCK))
        total_score += score

    # Average score if there are multiple garages
    return total_score / len(garages), True


def _evaluate_back_opening(room_points: list[OptunaScorePoint]) -> tuple[float, bool]:
    """
    Evaluates back clearance. Prioritizes the best score available.
    Kitchen base is 100. Hallway base is 70.
    Returns (score_out_of_100, is_evaluated)
    """
    kitchens = [r for r in room_points if r.room_type == ROOM_TYPE_KITCHEN]
    hallways = [r for r in room_points if r.room_type == ROOM_TYPE_HALLWAY]

    # Guard rail: Safety Gate to not damage the scoring if rooms don't exist
    if not kitchens and not hallways:
        return 0.0, False

    best_score = 0.0
    is_evaluated = False

    # Evaluate Kitchens (Base Score: 100)
    for k in kitchens:
        _, blockers = _box_is_clear(k, "back", room_points)
        score = max(0.0, 100.0 + (len(blockers) * PENALTY_PER_BLOCK))
        if score > best_score:
            best_score = score
        is_evaluated = True

    # Evaluate Hallways (Base Score: 70)
    for h in hallways:
        _, blockers = _box_is_clear(h, "back", room_points)
        score = max(0.0, 70.0 + (len(blockers) * PENALTY_PER_BLOCK))
        if score > best_score:
            best_score = score
        is_evaluated = True

    return best_score, is_evaluated


def score_outer_clearance(
    requirements: FpgRequirements, room_points: list[OptunaScorePoint]
) -> SectionScore:
    """
    Main orchestration function for Outer Clearance scoring.
    """
    if DEBUG_VERBOSE:
        print("\n--- Scoring Outer Clearance (Dynamic Architecture) ---")

    # 1. Define all active evaluators
    evaluators = [_evaluate_veranda, _evaluate_garage, _evaluate_back_opening]

    evaluated_count = 0
    received_score_total = 0.0

    # 2. Run evaluations
    for evaluate in evaluators:
        score, is_evaluated = evaluate(room_points)
        if is_evaluated:
            evaluated_count += 1
            received_score_total += score

    # 3. Fetch max score dynamically from project config
    max_section_score = float(OPTUNA_SCORING_VALUES.get("optuna_score_clearance", 0))

    # 4. Handle edge case: No rooms matched any evaluation gates
    if evaluated_count == 0:
        if DEBUG_VERBOSE:
            print("[-] No valid rooms found for clearance evaluation.")
        return SectionScore(
            score=max_section_score,
            max_score=max_section_score,
            details={"note": "No clearance rooms to evaluate, defaulting to full score"},
            warnings=[],
        )

    # 5. Calculate Final Score Base (out of 100)
    final_percentage_score = received_score_total / evaluated_count

    # 6. Normalize against the Optuna maximum allowed score
    normalized_final_score = (final_percentage_score / 100.0) * max_section_score

    if DEBUG_VERBOSE:
        print(f"[+] Evaluated Count: {evaluated_count}")
        print(f"[+] Total Percentage: {final_percentage_score:.2f}%")
        print(
            f"[+] Final Normalized Score: {normalized_final_score:.2f} / {max_section_score:.2f}"
        )

    return SectionScore(
        score=normalize_section_score(normalized_final_score, max_section_score),
        max_score=max_section_score,
        details={
            "evaluated_components": evaluated_count,
            "average_percentage_achieved": final_percentage_score,
        },
        warnings=[],
    )
"""Livability scoring from path simulation data.

4 metrics independently scored 0-100:
  1. Circulation Efficiency   – low traffic in living/kitchen zones
  2. Privacy Score            – public paths don't breach bedroom zones
  3. Hallway Utility          – hallway area actively used by paths
  4. Furniture Flexibility    – large quiet zones in living/bedrooms

Each metric is scored 0-100 independently, then weighted to contribute
to a final 0-100 total score. Normalization to fit score_margin is
handled by the caller (run_path_simulation.py).

No imports from outside this package.
"""

from __future__ import annotations

from typing import Any, List, Tuple

import numpy as np
from scipy import ndimage

from .pathfinder import ROOM_TYPE_CODES
from .. import path_sim_config
from ..types import PathResult, PathScoreResult
from ._dev_print import dev_print

# Import configuration from centralized config
_LIVING_CODE = ROOM_TYPE_CODES["livingRoom"]
_KITCHEN_CODE = ROOM_TYPE_CODES["kitchen"]
_BEDROOM_CODE = ROOM_TYPE_CODES["bedroom"]
_HALLWAY_CODE = ROOM_TYPE_CODES["hallway"]
_BATHROOM_CODES = {ROOM_TYPE_CODES["bathroom"], ROOM_TYPE_CODES["attachedBathroom"]}

PRIVACY_RADIUS_CM: float = path_sim_config.PRIVACY_RADIUS_CM
TARGET_QUIET_FRACTION: float = path_sim_config.TARGET_QUIET_FRACTION


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------


def _score_circulation_efficiency(
    traffic_map: np.ndarray,
    room_type_grid: np.ndarray,
    walkable: np.ndarray,
) -> float:
    """Score 0-100: less traffic in living / kitchen zones = better score."""
    mask = (
        (room_type_grid == _LIVING_CODE) | (room_type_grid == _KITCHEN_CODE)
    ) & walkable
    total = int(np.sum(mask))
    if total == 0:
        dev_print(
            "path",
            "Circulation: No living/kitchen rooms found. Returning neutral score.",
        )
        return 50.0  # neutral if no such rooms (50/100)

    traffic_cells = int(np.sum((traffic_map > 0) & mask))
    ratio = traffic_cells / total
    # Convert ratio (0-1) to score (0-100): less traffic = higher score
    score = _clamp(100.0 * (1.0 - ratio), 0.0, 100.0)

    dev_print(
        "path",
        f"Circulation: {traffic_cells}/{total} cells have traffic. Ratio: {ratio:.2%}, Score: {score:.2f}/100",
    )
    return score


def _score_privacy(
    traffic_map: np.ndarray,
    room_type_grid: np.ndarray,
    walkable: np.ndarray,
    paths: List[PathResult],
    bedroom_door_pts: List[Tuple[float, float]],
    grid_resolution: float,
    grid_min_x: float,
    grid_min_y: float,
    grid_h: int,
    grid_w: int,
) -> float:
    """Score 0-100: public paths (entry→kitchen/bathroom) must not breach bedroom zones."""
    if not bedroom_door_pts:
        dev_print("path", "Privacy: No bedroom doors found. Returning max score.")
        return 100.0  # no bedrooms → no privacy concern (100/100)

    privacy_cells = max(1, int(PRIVACY_RADIUS_CM / grid_resolution))
    num_bedrooms = len(bedroom_door_pts)
    breaches = 0

    # Build public-path traffic mask
    public_traffic = np.zeros_like(traffic_map, dtype=bool)
    public_path_count = 0
    for path in paths:
        if not path.is_public:
            continue
        public_path_count += 1
        for x, y in path.coords:
            ix = int((x - grid_min_x) / grid_resolution)
            iy = int((y - grid_min_y) / grid_resolution)
            ix = max(0, min(grid_w - 1, ix))
            iy = max(0, min(grid_h - 1, iy))
            public_traffic[iy, ix] = True

    if not np.any(public_traffic):
        dev_print("path", "Privacy: No public paths simulated. Returning max score.")
        return 100.0

    # Dilate to get "public traffic zone"
    struct = ndimage.generate_binary_structure(2, 2)
    dilated = ndimage.binary_dilation(
        public_traffic, structure=struct, iterations=privacy_cells
    )

    for bx, by in bedroom_door_pts:
        ix = int((bx - grid_min_x) / grid_resolution)
        iy = int((by - grid_min_y) / grid_resolution)
        ix = max(0, min(grid_w - 1, ix))
        iy = max(0, min(grid_h - 1, iy))
        if dilated[iy, ix]:
            breaches += 1

    breach_ratio = breaches / num_bedrooms
    # Convert breach ratio (0-1) to score (0-100): fewer breaches = higher score
    score = _clamp(100.0 * (1.0 - breach_ratio), 0.0, 100.0)

    dev_print(
        "path",
        f"Privacy: {breaches} breaches in {num_bedrooms} bedrooms (Public paths: {public_path_count}). Score: {score:.2f}/100",
    )
    return score


def _score_hallway_utility(
    traffic_map: np.ndarray,
    room_type_grid: np.ndarray,
    walkable: np.ndarray,
) -> float:
    """Score 0-100: high proportion of hallway area covered by at least one path."""
    hallway_mask = (room_type_grid == _HALLWAY_CODE) & walkable
    total_hallway = int(np.sum(hallway_mask))
    if total_hallway == 0:
        dev_print("path", "Hallway: No hallway cells found. Returning neutral score.")
        return 50.0  # neutral – no hallways present (50/100)

    used = int(np.sum((traffic_map > 0) & hallway_mask))
    ratio = used / total_hallway
    # Convert utilization ratio (0-1) to score (0-100)
    score = _clamp(100.0 * ratio, 0.0, 100.0)

    dev_print(
        "path",
        f"Hallway: {used}/{total_hallway} cells used. Utilization: {ratio:.2%}, Score: {score:.2f}/100",
    )
    return score


def _score_furniture_flexibility(
    traffic_map: np.ndarray,
    room_type_grid: np.ndarray,
    walkable: np.ndarray,
) -> float:
    """Score 0-100: largest contiguous quiet zone in living + bedrooms."""
    living_bed_mask = (
        (room_type_grid == _LIVING_CODE) | (room_type_grid == _BEDROOM_CODE)
    ) & walkable
    total_lb = int(np.sum(living_bed_mask))
    if total_lb == 0:
        dev_print(
            "path", "Furniture: No living/bedroom area found. Returning neutral score."
        )
        return 50.0  # neutral (50/100)

    quiet_mask = (traffic_map == 0) & living_bed_mask
    if not np.any(quiet_mask):
        dev_print("path", "Furniture: No quiet zones found. Score: 0.0")
        return 0.0

    labeled, num_features = ndimage.label(quiet_mask)
    if num_features == 0:
        return 0.0

    sizes = ndimage.sum(quiet_mask, labeled, range(1, num_features + 1))
    largest_cc = int(np.max(sizes))
    quiet_fraction = largest_cc / total_lb
    # Score based on how much the largest quiet zone meets the target
    # If it exceeds the target, cap at 100; below target, scale proportionally
    score = _clamp(100.0 * min(1.0, quiet_fraction / TARGET_QUIET_FRACTION), 0.0, 100.0)

    dev_print(
        "path",
        f"Furniture: Largest quiet zone is {largest_cc} cells. Fraction: {quiet_fraction:.2%} (Target: {TARGET_QUIET_FRACTION:.0%}), Score: {score:.2f}/100",
    )
    return score


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def score_path_simulation(
    grid: Any,  # AStarGrid instance
    paths: List[PathResult],
    bedroom_door_pts: List[Tuple[float, float]],
    score_margin: float = 100.0,
) -> PathScoreResult:
    """Compute the 4 livability metrics and return a PathScoreResult.

    Each metric is scored 0-100 independently, then weighted to compute
    a final 0-100 total score. Scores can then be normalized by the caller
    using score_margin.

    Parameters
    ----------
    grid : AStarGrid
        The rasterized and labeled grid.
    paths : List[PathResult]
        All simulated paths.
    bedroom_door_pts : List[Tuple[float, float]]
        Bedroom door anchor points for privacy scoring.
    score_margin : float
        Optional margin to normalize scores (default 100.0 = no change).

    Returns
    -------
    PathScoreResult with individual 0-100 scores and normalized total.
    """
    dev_print(
        "path",
        f"--- Starting Scoring Simulation (Paths: {len(paths)}, Doors: {len(bedroom_door_pts)}) ---",
    )

    if grid.walkable is None or grid.traffic_map is None or grid.room_type_grid is None:
        dev_print("path", "Scoring Error: Grid not rasterized.")
        return PathScoreResult(
            total_score=0.0,
            circulation_efficiency=0.0,
            privacy_score=0.0,
            hallway_utility=0.0,
            furniture_flexibility=0.0,
            paths=paths,
            error="Grid not rasterized.",
        )

    traffic_map: np.ndarray = grid.traffic_map
    room_type_grid: np.ndarray = grid.room_type_grid
    walkable: np.ndarray = grid.walkable
    res: float = grid.resolution
    min_x, min_y, _, _ = grid.bounds
    h, w = grid._height, grid._width

    # Get raw 0-100 scores from each metric
    circ = _score_circulation_efficiency(traffic_map, room_type_grid, walkable)
    priv = _score_privacy(
        traffic_map,
        room_type_grid,
        walkable,
        paths,
        bedroom_door_pts,
        res,
        min_x,
        min_y,
        h,
        w,
    )
    hall = _score_hallway_utility(traffic_map, room_type_grid, walkable)
    furn = _score_furniture_flexibility(traffic_map, room_type_grid, walkable)

    # Apply weights from config
    weights = path_sim_config.SCORE_WEIGHTS
    weighted_circ = circ * weights["circulation_efficiency"]
    weighted_priv = priv * weights["privacy_score"]
    weighted_hall = hall * weights["hallway_utility"]
    weighted_furn = furn * weights["furniture_flexibility"]
    weighted_total = weighted_circ + weighted_priv + weighted_hall + weighted_furn

    # Normalize to score_margin and clamp
    total = _clamp(weighted_total, 0.0, 100.0)

    # Normalize individual scores to fit score_margin
    normalized_circ = round((circ / 100.0) * score_margin, 2)
    normalized_priv = round((priv / 100.0) * score_margin, 2)
    normalized_hall = round((hall / 100.0) * score_margin, 2)
    normalized_furn = round((furn / 100.0) * score_margin, 2)
    normalized_total = round((total / 100.0) * score_margin, 2)

    dev_print(
        "path",
        {
            "raw_scores": {
                "circulation": circ,
                "privacy": priv,
                "hallway": hall,
                "furniture": furn,
                "total": total,
            },
            "normalized_scores": {
                "circulation": normalized_circ,
                "privacy": normalized_priv,
                "hallway": normalized_hall,
                "furniture": normalized_furn,
                "total": normalized_total,
            },
            "score_margin": score_margin,
        },
    )

    return PathScoreResult(
        total_score=normalized_total,
        circulation_efficiency=normalized_circ,
        privacy_score=normalized_priv,
        hallway_utility=normalized_hall,
        furniture_flexibility=normalized_furn,
        paths=paths,
        details={
            "traffic_cells_pct": float(
                np.sum(traffic_map > 0) / max(1, np.sum(walkable)) * 100
            ),
            "walkable_cells": int(np.sum(walkable)),
            "num_paths": len(paths),
            "score_margin_applied": score_margin,
            "score_breakdown": {
                "raw_0_to_100": {
                    "circulation_efficiency": round(circ, 4),
                    "privacy_score": round(priv, 4),
                    "hallway_utility": round(hall, 4),
                    "furniture_flexibility": round(furn, 4),
                },
                "weights": {
                    "circulation_efficiency": weights["circulation_efficiency"],
                    "privacy_score": weights["privacy_score"],
                    "hallway_utility": weights["hallway_utility"],
                    "furniture_flexibility": weights["furniture_flexibility"],
                },
                "weighted_contribution_0_to_100": {
                    "circulation_efficiency": round(weighted_circ, 4),
                    "privacy_score": round(weighted_priv, 4),
                    "hallway_utility": round(weighted_hall, 4),
                    "furniture_flexibility": round(weighted_furn, 4),
                },
                "weighted_total_0_to_100": round(total, 4),
                "normalized_total_0_to_score_margin": round(normalized_total, 4),
            },
        },
    )

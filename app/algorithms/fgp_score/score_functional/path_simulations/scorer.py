"""Livability scoring from path simulation data.

4 metrics totalling 100 points:
  1. Circulation Efficiency   (30 pts) – low traffic in living/kitchen
  2. Privacy Score            (25 pts) – public paths don't breach bedroom zones
  3. Hallway Utility          (25 pts) – hallway area actively used by paths
  4. Furniture Flexibility    (20 pts) – large quiet zones in living/bedrooms

No imports from outside this package.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import ndimage

from .pathfinder import ROOM_TYPE_CODES
from .types import PathResult, PathScoreResult

# Constants
PRIVACY_RADIUS_CM: float = 150.0   # cm around a bedroom door = "privacy zone"
TARGET_QUIET_FRACTION: float = 0.35  # fraction of living/bed area we want traffic-free

_LIVING_CODE = ROOM_TYPE_CODES["livingRoom"]
_KITCHEN_CODE = ROOM_TYPE_CODES["kitchen"]
_BEDROOM_CODE = ROOM_TYPE_CODES["bedroom"]
_HALLWAY_CODE = ROOM_TYPE_CODES["hallway"]
_BATHROOM_CODES = {ROOM_TYPE_CODES["bathroom"], ROOM_TYPE_CODES["attachedBathroom"]}


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
    """30 pts: less traffic in living / kitchen zones = better."""
    mask = (
        ((room_type_grid == _LIVING_CODE) | (room_type_grid == _KITCHEN_CODE))
        & walkable
    )
    total = int(np.sum(mask))
    if total == 0:
        return 20.0  # neutral if no such rooms
    traffic_cells = int(np.sum((traffic_map > 0) & mask))
    ratio = traffic_cells / total
    return _clamp(30.0 * (1.0 - ratio), 0.0, 30.0)


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
    """25 pts: public paths (entry→kitchen/bathroom) must not enter bedroom zones."""
    if not bedroom_door_pts:
        return 25.0  # no bedrooms → no privacy concern

    privacy_cells = max(1, int(PRIVACY_RADIUS_CM / grid_resolution))
    num_bedrooms = len(bedroom_door_pts)
    breaches = 0

    # Build public-path traffic mask
    public_traffic = np.zeros_like(traffic_map, dtype=bool)
    for path in paths:
        if not path.is_public:
            continue
        for x, y in path.coords:
            ix = int((x - grid_min_x) / grid_resolution)
            iy = int((y - grid_min_y) / grid_resolution)
            ix = max(0, min(grid_w - 1, ix))
            iy = max(0, min(grid_h - 1, iy))
            public_traffic[iy, ix] = True

    if not np.any(public_traffic):
        return 25.0

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
    return _clamp(25.0 * (1.0 - breach_ratio), 0.0, 25.0)


def _score_hallway_utility(
    traffic_map: np.ndarray,
    room_type_grid: np.ndarray,
    walkable: np.ndarray,
) -> float:
    """25 pts: high proportion of hallway area covered by at least one path."""
    hallway_mask = (room_type_grid == _HALLWAY_CODE) & walkable
    total_hallway = int(np.sum(hallway_mask))
    if total_hallway == 0:
        return 18.0  # neutral – no hallways present
    used = int(np.sum((traffic_map > 0) & hallway_mask))
    ratio = used / total_hallway
    return _clamp(25.0 * ratio, 0.0, 25.0)


def _score_furniture_flexibility(
    traffic_map: np.ndarray,
    room_type_grid: np.ndarray,
    walkable: np.ndarray,
) -> float:
    """20 pts: largest contiguous quiet zone in living + bedrooms."""
    living_bed_mask = (
        ((room_type_grid == _LIVING_CODE) | (room_type_grid == _BEDROOM_CODE))
        & walkable
    )
    total_lb = int(np.sum(living_bed_mask))
    if total_lb == 0:
        return 10.0  # neutral

    quiet_mask = (traffic_map == 0) & living_bed_mask
    if not np.any(quiet_mask):
        return 0.0

    labeled, num_features = ndimage.label(quiet_mask)
    if num_features == 0:
        return 0.0

    sizes = ndimage.sum(quiet_mask, labeled, range(1, num_features + 1))
    largest_cc = int(np.max(sizes))
    quiet_fraction = largest_cc / total_lb
    return _clamp(20.0 * min(1.0, quiet_fraction / TARGET_QUIET_FRACTION), 0.0, 20.0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_path_simulation(
    grid: Any,  # AStarGrid instance
    paths: List[PathResult],
    bedroom_door_pts: List[Tuple[float, float]],
) -> PathScoreResult:
    """Compute the 4 livability metrics and return a PathScoreResult."""
    if grid.walkable is None or grid.traffic_map is None or grid.room_type_grid is None:
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

    circ = _score_circulation_efficiency(traffic_map, room_type_grid, walkable)
    priv = _score_privacy(
        traffic_map, room_type_grid, walkable, paths,
        bedroom_door_pts, res, min_x, min_y, h, w,
    )
    hall = _score_hallway_utility(traffic_map, room_type_grid, walkable)
    furn = _score_furniture_flexibility(traffic_map, room_type_grid, walkable)

    total = _clamp(circ + priv + hall + furn, 0.0, 100.0)

    return PathScoreResult(
        total_score=round(total, 2),
        circulation_efficiency=round(circ, 2),
        privacy_score=round(priv, 2),
        hallway_utility=round(hall, 2),
        furniture_flexibility=round(furn, 2),
        paths=paths,
        details={
            "traffic_cells_pct": float(
                np.sum(traffic_map > 0) / max(1, np.sum(walkable)) * 100
            ),
            "walkable_cells": int(np.sum(walkable)),
            "num_paths": len(paths),
        },
    )

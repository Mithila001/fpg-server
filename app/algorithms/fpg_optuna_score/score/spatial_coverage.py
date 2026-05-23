from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

from test.plotters.spatial_coverage import save_spatial_coverage_heatmap

# Force Matplotlib to use the non-interactive 'Agg' backend.
# CRITICAL for backend servers/Optuna workers to prevent UI thread crashes and memory leaks.
matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.patheffects as patheffects
import numpy as np
from scipy.spatial import KDTree

from app.algorithms.fpg_optuna_score.util.scoring_common import (
    OptunaScorePoint,
    SectionScore,
    normalize_section_score,
)
from app.algorithms.types.domain import FpgRequirements
from app.core.fpg_rooms.config_fpg import OPTUNA_SCORING_VALUES


max_score_limit = OPTUNA_SCORING_VALUES.get("optuna_score_spatial_coverage", 0)

# Grid resolution for Space-to-Point gap detection.
SPATIAL_COVERAGE_ZONE_GRID_SCALE = 20

# NND uniformity: CV sensitivity (higher = more tolerant of spread).
POINT_SPREAD_DISCREPANCY = 8.0

# Weight between NND uniformity score and Grid-Sampling gap score (must sum to 1.0).
NND_WEIGHT = 0.40
GRID_WEIGHT = 0.60

HEATMAP_OUTPUT_DIR = (
    Path(__file__).parent.parent.parent.parent.parent
    / "test"
    / "outputs"
    / "optuna_score"
    / "spatial_coverage"
)

# Only save plots when the score is at least this percent of the maximum score.

PLOT_THRESHOLD_PERCENT = 40  # Matches "2.5 out of 10" request


# ---------------------------------------------------------------------------
# NND sub-score  (anti-clumping)
# ---------------------------------------------------------------------------
def _calculate_nnd_score(
    room_points: list[OptunaScorePoint],
    floor_width: float,
    floor_height: float,
) -> tuple[float, dict[str, float]]:
    """
    Nearest-Neighbour Distance (NND) uniformity score (0-100).
    Uses Coefficient of Variation (CV = std/mean) for robust uniformity scoring.
    Includes boundary anchors to prevent artificial center-clustering.
    """
    floor_area = floor_width * floor_height
    n = len(room_points)

    room_xy = np.array([(p.x, p.y) for p in room_points], dtype=np.float64)

    # Boundary anchors: 4 corners + 8 edge points
    bx, by = floor_width, floor_height
    boundary_xy = np.array(
        [
            (0.0, 0.0),
            (bx, 0.0),
            (bx, by),
            (0.0, by),
            (bx / 2, 0.0),
            (bx / 2, by),
            (0.0, by / 2),
            (bx, by / 2),
            (bx / 4, 0.0),
            (3 * bx / 4, 0.0),
            (bx / 4, by),
            (3 * bx / 4, by),
        ],
        dtype=np.float64,
    )

    # Room-to-Room NND
    room_tree = KDTree(room_xy)
    if n > 1:
        rr_dists, _ = room_tree.query(room_xy, k=2)
        min_rr = rr_dists[:, 1]  # skip self (distance 0)
    else:
        min_rr = np.full(n, np.inf)

    # Room-to-Boundary distance
    boundary_tree = KDTree(boundary_xy)
    rb_dists, _ = boundary_tree.query(room_xy, k=1)
    min_rb = rb_dists

    # Effective NND per point: min(room-to-room, room-to-boundary)
    nnd_array = np.minimum(min_rr, min_rb)
    mean_nnd = float(np.mean(nnd_array))
    std_nnd = float(np.std(nnd_array))

    # Uniformity via Coefficient of Variation (CV)
    # Lower CV = more uniform spacing. CV=0 → 100, CV=0.5 → ~1.8
    cv = std_nnd / max(mean_nnd, 1e-9)
    exponent = max(-cv * POINT_SPREAD_DISCREPANCY, -10.0)
    uniformity = 100.0 * math.exp(exponent)

    ideal_distance = math.sqrt(floor_area / n) if n > 0 else 0.0

    return float(np.clip(uniformity, 0.0, 100.0)), {
        "mean_nnd": mean_nnd,
        "std_nnd": std_nnd,
        "ideal_distance": ideal_distance,
        "nnd_array": nnd_array.tolist(),
    }


# ---------------------------------------------------------------------------
# Grid-Sampling sub-score  (anti-gap / void detection)
# ---------------------------------------------------------------------------
def _calculate_grid_sampling_score(
    room_points: list[OptunaScorePoint],
    floor_width: float,
    floor_height: float,
) -> tuple[float, dict[str, Any]]:
    """
    Grid-Sampling (Space-to-Point) gap score (0-100).
    Uses 95th-percentile gap to avoid single-probe outliers killing the score.
    Normalizes against theoretical optimal coverage radius (ideal/√2).
    """
    g = SPATIAL_COVERAGE_ZONE_GRID_SCALE
    n = len(room_points)

    # Build probe grid
    xs = np.linspace(0.0, floor_width, g, dtype=np.float64)
    ys = np.linspace(0.0, floor_height, g, dtype=np.float64)
    gx, gy = np.meshgrid(xs, ys)
    probe_xy = np.column_stack([gx.ravel(), gy.ravel()])

    room_xy = np.array([(p.x, p.y) for p in room_points], dtype=np.float64)
    room_tree = KDTree(room_xy)
    probe_dists, _ = room_tree.query(probe_xy, k=1)

    # Use 95th percentile to ignore edge-case outliers while capturing true voids
    max_gap = float(np.percentile(probe_dists, 95))
    mean_gap = float(np.mean(probe_dists))

    # Theoretical optimal max-gap for n points covering area A:
    # ideal_coverage_radius = √(A/n) / √2  (square tiling geometry)
    floor_area = floor_width * floor_height
    ideal_distance = math.sqrt(floor_area / n) if n > 0 else 1.0
    theoretical_min_max_gap = ideal_distance / math.sqrt(2.0)

    # Ratio: 1.0 = perfect coverage, >1.5 = severe voids → score 0
    normalised_gap = max_gap / max(theoretical_min_max_gap, 1e-9)
    score = float(np.clip(100.0 * (1.0 - (normalised_gap - 1.0) / 0.5), 0.0, 100.0))

    return score, {
        "grid_scale": g,
        "max_gap": max_gap,
        "mean_gap": mean_gap,
        "ideal_distance_grid": ideal_distance,
        "theoretical_min_max_gap": theoretical_min_max_gap,
        "normalised_gap": normalised_gap,
        "probe_dists": probe_dists.reshape(g, g).tolist(),
        "probe_xy": probe_xy.tolist(),
    }


# ---------------------------------------------------------------------------
# Public scoring function
# ---------------------------------------------------------------------------
def score_spatial_coverage(
    requirements: FpgRequirements, room_points: list[OptunaScorePoint]
) -> SectionScore:
    warnings: list[str] = []
    floor_width = requirements.config.floor_plan_width
    floor_height = requirements.config.floor_plan_height
    floor_area = floor_width * floor_height

    if not room_points:
        warnings.append("No room points provided; spatial coverage score is 0.")
        details = {
            "final_score": 0.0,
            "max_score": max_score_limit,
            "nnd_score_100": 0.0,
            "grid_score_100": 0.0,
            "mean_nnd": 0.0,
            "std_nnd": 0.0,
            "ideal_distance": 0.0,
            "max_gap": 0.0,
            "mean_gap": 0.0,
            "normalised_gap": 0.0,
            "num_room_points": 0,
            "floor_area": floor_area,
            "grid_scale": SPATIAL_COVERAGE_ZONE_GRID_SCALE,
        }
        save_spatial_coverage_heatmap(room_points, requirements, details)
        return SectionScore(0.0, max_score_limit, details, warnings)

    nnd_score_100, nnd_debug = _calculate_nnd_score(
        room_points, floor_width, floor_height
    )
    grid_score_100, grid_debug = _calculate_grid_sampling_score(
        room_points, floor_width, floor_height
    )

    combined_100 = (NND_WEIGHT * nnd_score_100) + (GRID_WEIGHT * grid_score_100)
    combined_100 = float(np.clip(combined_100, 0.0, 100.0))

    final_score = normalize_section_score(
        combined_100 / 100.0 * max_score_limit, max_score_limit
    )

    if nnd_debug["std_nnd"] > nnd_debug["mean_nnd"] * 0.8:
        warnings.append(
            f"High NND variation (CV={nnd_debug['std_nnd'] / max(nnd_debug['mean_nnd'], 1e-9):.2f}) → irregular clustering."
        )
    if grid_debug["normalised_gap"] > 1.3:
        warnings.append(
            f"Coverage voids detected: gap ratio={grid_debug['normalised_gap']:.2f}× theoretical optimum."
        )
    print(
        f"[Debug] Spatial Coverage - Final Score: {final_score:.2f} / {max_score_limit}"
    )

    scoring_details = {
        "final_score": final_score,
        "max_score": max_score_limit,
        "combined_100": combined_100,
        "nnd_score_100": nnd_score_100,
        "grid_score_100": grid_score_100,
        "nnd_weight": NND_WEIGHT,
        "grid_weight": GRID_WEIGHT,
        "mean_nnd": nnd_debug["mean_nnd"],
        "std_nnd": nnd_debug["std_nnd"],
        "ideal_distance": nnd_debug["ideal_distance"],
        "nnd_array": nnd_debug["nnd_array"],
        "grid_scale": grid_debug["grid_scale"],
        "max_gap": grid_debug["max_gap"],
        "mean_gap": grid_debug["mean_gap"],
        "normalised_gap": grid_debug["normalised_gap"],
        "ideal_distance_grid": grid_debug["ideal_distance_grid"],
        "probe_dists": grid_debug["probe_dists"],
        "num_room_points": len(room_points),
        "floor_area": floor_area,
    }

    # save_spatial_coverage_heatmap(room_points, requirements, scoring_details)
    return SectionScore(final_score, max_score_limit, scoring_details, warnings)

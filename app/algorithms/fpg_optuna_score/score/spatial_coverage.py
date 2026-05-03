from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

# Force Matplotlib to use the non-interactive 'Agg' backend.
# CRITICAL for backend servers/Optuna workers to prevent UI thread crashes and memory leaks.
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial.distance import cdist

from app.algorithms.fpg_optuna_score.util.scoring_common import (
    OptunaScorePoint,
    SectionScore,
    normalize_section_score,
)
from app.algorithms.types.domain import FpgRequirements
from app.core.fpg_rooms.config_fpg import OPTUNA_SCORING_VALUES

max_score_limit = OPTUNA_SCORING_VALUES.get("optuna_score_spatial_coverage", 10)

# Adjustable sensitivity parameter: controls tolerance for irregularity in NND.
POINT_SPREAD_DISCREPANCY = 10

# Density threshold multipliers for clumping/gap penalties
CLUMP_THRESHOLD = 0.75  # If mean_nnd < ideal * CLUMP_THRESHOLD, apply clumping penalty
GAP_THRESHOLD = 1.25  # If mean_nnd > ideal * GAP_THRESHOLD, apply gap penalty

HEATMAP_OUTPUT_DIR = (
    Path(__file__).parent.parent.parent.parent.parent
    / "test"
    / "outputs"
    / "optuna_score"
    / "spatial_coverage"
)


def _get_boundary_virtual_points(
    floor_width: float, floor_height: float
) -> list[tuple[float, float]]:
    """Generate 12 virtual boundary points to ensure edge-respecting optimization."""
    corners = [
        (0.0, 0.0),
        (floor_width, 0.0),
        (floor_width, floor_height),
        (0.0, floor_height),
    ]

    edge_midpoints = [
        (floor_width / 2.0, 0.0),
        (floor_width / 2.0, floor_height),
        (0.0, floor_height / 2.0),
        (floor_width, floor_height / 2.0),
        (floor_width / 4.0, 0.0),
        (3.0 * floor_width / 4.0, 0.0),
        (floor_width / 4.0, floor_height),
        (3.0 * floor_width / 4.0, floor_height),
    ]
    return corners + edge_midpoints


def _calculate_ideal_distance(floor_area: float, num_points: int) -> float:
    """Calculate theoretical ideal spacing based on point density."""
    return math.sqrt(floor_area / num_points) if num_points > 0 else 0.0


def _calculate_nnd_metrics(
    room_points: list[OptunaScorePoint],
    boundary_points: list[tuple[float, float]],
) -> tuple[float, float, list[float]]:
    """
    Calculate Nearest Neighbor Distance (NND) metrics for ROOM points only.
    The nearest neighbor can be another room point or a boundary point.
    """
    if not room_points:
        return 0.0, 0.0, []

    room_array = np.array([(p.x, p.y) for p in room_points], dtype=np.float64)
    boundary_array = np.array(boundary_points, dtype=np.float64)

    # 1. Distances between room points (ignore self by filling diagonal with infinity)
    if len(room_points) > 1:
        rr_dist = cdist(room_array, room_array, metric="euclidean")
        np.fill_diagonal(rr_dist, np.inf)
        min_rr = np.min(rr_dist, axis=1)
    else:
        min_rr = np.full(len(room_points), np.inf)

    # 2. Distances from room points to boundary points
    rb_dist = cdist(room_array, boundary_array, metric="euclidean")
    min_rb = np.min(rb_dist, axis=1)

    # 3. The true nearest neighbor for each room point is the minimum of the two
    nnd_array = np.minimum(min_rr, min_rb)

    return float(np.mean(nnd_array)), float(np.std(nnd_array)), nnd_array.tolist()


def _compute_density_penalty(mean_nnd: float, ideal_distance: float) -> float:
    """Compute penalty factor (0.0 to 1.0) where 1.0 is a perfect score (no penalty)."""
    if ideal_distance <= 0.0:
        return 1.0

    clump_lower = ideal_distance * CLUMP_THRESHOLD
    gap_upper = ideal_distance * GAP_THRESHOLD

    if mean_nnd < clump_lower:
        return max(0.0, mean_nnd / clump_lower)
    elif mean_nnd > gap_upper:
        excess = mean_nnd - ideal_distance
        max_excess = ideal_distance * (GAP_THRESHOLD - 1.0)
        if max_excess <= 0.0:
            return 1.0
        return max(0.0, 1.0 - (excess / max_excess))

    return 1.0


def _compute_uniformity_score(
    std_dev_nnd: float, point_spread_discrepancy: float = POINT_SPREAD_DISCREPANCY
) -> float:
    """Convert NND std_dev into a 0-100 uniformity score using exponential decay."""
    if std_dev_nnd < 0.0 or point_spread_discrepancy <= 0.0:
        return 0.0

    exponent = max(-std_dev_nnd / point_spread_discrepancy, -10.0)
    return min(100.0, max(0.0, 100.0 * math.exp(exponent)))


def _compute_edge_coverage_score(
    room_points: list[OptunaScorePoint],
    boundary_virtual_points: list[tuple[float, float]],
    ideal_distance: float,
) -> float:
    """Calculate how well the generated points cover the room boundaries."""
    if not room_points or not boundary_virtual_points:
        return 0.0
    if ideal_distance <= 0.0:
        return 100.0

    room_array = np.array([(p.x, p.y) for p in room_points], dtype=np.float64)
    boundary_array = np.array(boundary_virtual_points, dtype=np.float64)

    distances = cdist(boundary_array, room_array, metric="euclidean")
    min_distances = np.min(distances, axis=1)

    # Vectorized score calculation for edge coverage
    excess_ratios = np.maximum(0, (min_distances - ideal_distance) / ideal_distance)
    scores = np.maximum(0, 100.0 * (1.0 - excess_ratios))

    return float(np.mean(scores))


def _save_spatial_coverage_heatmap(
    room_points: list[OptunaScorePoint],
    requirements: FpgRequirements,
    scoring_details: dict[str, Any],
) -> None:
    """Create and save a visualization heatmap showing spatial coverage scoring breakdown."""
    try:
        HEATMAP_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        floor_width = requirements.config.floor_plan_width
        floor_height = requirements.config.floor_plan_height

        fig, ax = plt.subplots(figsize=(12, 10))

        # Floor boundary
        ax.add_patch(
            mpatches.Rectangle(
                (0, 0),
                floor_width,
                floor_height,
                linewidth=2,
                edgecolor="black",
                facecolor="lightgray",
                alpha=0.1,
            )
        )

        # Room points
        if room_points:
            room_x = [p.x for p in room_points]
            room_y = [p.y for p in room_points]
            ax.scatter(
                room_x,
                room_y,
                c="blue",
                s=100,
                marker="o",
                label="Room Points",
                edgecolors="darkblue",
                linewidth=1.5,
                zorder=5,
            )
            for p in room_points:
                ax.annotate(
                    p.name,
                    (p.x, p.y),
                    xytext=(5, 5),
                    textcoords="offset points",
                    fontsize=8,
                    alpha=0.7,
                )

            # Plot ideal distance circle around first room point for reference
            ideal_dist = scoring_details.get("ideal_distance", 0)
            if ideal_dist > 0:
                ax.add_patch(
                    mpatches.Circle(
                        (room_points[0].x, room_points[0].y),
                        ideal_dist,
                        color="green",
                        fill=False,
                        linestyle="--",
                        linewidth=1.5,
                        label=f"Ideal Distance (D={ideal_dist:.2f})",
                        alpha=0.6,
                        zorder=3,
                    )
                )

        # Virtual boundary points
        boundary_points = _get_boundary_virtual_points(floor_width, floor_height)
        if boundary_points:
            bound_x, bound_y = zip(*boundary_points)
            ax.scatter(
                bound_x,
                bound_y,
                c="red",
                s=50,
                marker="x",
                label="Virtual Boundary Points",
                linewidth=2,
                zorder=4,
            )

        ax.set_xlim(-5, floor_width + 5)
        ax.set_ylim(-5, floor_height + 5)
        ax.set_aspect("equal")
        ax.grid(True, alpha=0.3, linestyle=":")
        ax.set_xlabel("X (Floor Width)", fontsize=10)
        ax.set_ylabel("Y (Floor Height)", fontsize=10)

        title_parts = [
            "Spatial Coverage Scoring Heatmap\n",
            f"Final Score: {scoring_details.get('final_score', 0):.2f} / {scoring_details.get('max_score', 10)}\n",
            f"Mean NND: {scoring_details.get('mean_nnd', 0):.2f} | Std Dev: {scoring_details.get('std_dev_nnd', 0):.2f}\n",
            f"Uniformity: {scoring_details.get('uniformity_score', 0):.1f}% | Edge Coverage: {scoring_details.get('edge_coverage_score', 0):.1f}% | Density Multiplier: {scoring_details.get('density_penalty', 1):.2f}x",
        ]
        ax.set_title("".join(title_parts), fontsize=11, fontweight="bold")
        ax.legend(loc="upper right", fontsize=9)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plt.savefig(
            HEATMAP_OUTPUT_DIR / f"heatmap_{timestamp}.png",
            dpi=100,
            bbox_inches="tight",
        )

    except Exception as e:
        print(f"[Warning] Failed to save spatial coverage heatmap: {e}")
    finally:
        plt.close("all")  # Guarantee memory is freed


def score_spatial_coverage(
    requirements: FpgRequirements, room_points: list[OptunaScorePoint]
) -> SectionScore:
    """Score spatial coverage using Low-Discrepancy Dispersion analysis."""
    warnings: list[str] = []

    floor_width = requirements.config.floor_plan_width
    floor_height = requirements.config.floor_plan_height
    floor_area = floor_width * floor_height

    if not room_points:
        warnings.append("No room points provided; spatial coverage score is 0.")
        details = {
            "final_score": 0.0,
            "max_score": max_score_limit,
            "mean_nnd": 0.0,
            "std_dev_nnd": 0.0,
            "ideal_distance": 0.0,
            "uniformity_score": 0.0,
            "edge_coverage_score": 0.0,
            "density_penalty": 1.0,
        }
        _save_spatial_coverage_heatmap(room_points, requirements, details)
        return SectionScore(
            score=0.0, max_score=max_score_limit, details=details, warnings=warnings
        )

    num_room_points = len(room_points)
    ideal_distance = _calculate_ideal_distance(floor_area, num_room_points)
    boundary_points = _get_boundary_virtual_points(floor_width, floor_height)

    mean_nnd, std_dev_nnd, _ = _calculate_nnd_metrics(room_points, boundary_points)

    uniformity_score = _compute_uniformity_score(std_dev_nnd)
    edge_coverage_score = _compute_edge_coverage_score(
        room_points, boundary_points, ideal_distance
    )
    density_penalty = _compute_density_penalty(mean_nnd, ideal_distance)

    # Mathematical fix applied here: density_penalty correctly multiplies base distribution score
    raw_internal_score = (
        (uniformity_score * 0.60)
        + (edge_coverage_score * 0.30)
        + (density_penalty * 100.0 * 0.10)
    )

    raw_internal_score = max(0.0, min(100.0, raw_internal_score))
    final_score = normalize_section_score(raw_internal_score / 10.0, max_score_limit)

    scoring_details = {
        "final_score": final_score,
        "max_score": max_score_limit,
        "raw_internal_score": raw_internal_score,
        "floor_area": floor_area,
        "num_room_points": num_room_points,
        "ideal_distance": ideal_distance,
        "mean_nnd": mean_nnd,
        "std_dev_nnd": std_dev_nnd,
        "uniformity_score": uniformity_score,
        "edge_coverage_score": edge_coverage_score,
        "density_penalty": density_penalty,
    }

    _save_spatial_coverage_heatmap(room_points, requirements, scoring_details)

    if std_dev_nnd > ideal_distance * 2.0:
        warnings.append(
            f"High NND standard deviation ({std_dev_nnd:.2f}) suggests irregular distribution."
        )
    if density_penalty < 0.5:
        if mean_nnd < ideal_distance * CLUMP_THRESHOLD:
            warnings.append(
                f"Points are clustering (mean_nnd={mean_nnd:.2f} << ideal={ideal_distance:.2f})."
            )
        else:
            warnings.append(
                f"Points have excessive gaps (mean_nnd={mean_nnd:.2f} >> ideal={ideal_distance:.2f})."
            )

    return SectionScore(
        score=final_score,
        max_score=max_score_limit,
        details=scoring_details,
        warnings=warnings,
    )

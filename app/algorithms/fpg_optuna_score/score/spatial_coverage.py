from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

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
# A 20x20 grid of probe points is generated across the floor plan.
# The max distance from any probe to its nearest room point is the gap penalty.
SPATIAL_COVERAGE_ZONE_GRID_SCALE = 20

# NND uniformity: std-dev sensitivity (higher = more tolerant of spread).
POINT_SPREAD_DISCREPANCY = 10.0

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

# Only save plots when the score is at least this percent of the max score.
# User requested "2.5 out of 10" → interpreted as 25% threshold.
PLOT_THRESHOLD_PERCENT = 80

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

    Each room point's nearest neighbour can be another room point or a
    boundary anchor — this prevents all points from clustering at the centre
    while still far from each other by absolute distance.

    Returns (score_0_100, debug_dict).
    """
    floor_area = floor_width * floor_height
    n = len(room_points)

    room_xy = np.array([(p.x, p.y) for p in room_points], dtype=np.float64)

    # Boundary anchors: 4 corners + 8 edge mid/quarter points
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

    # NND: nearest neighbour per room point (room-to-room or room-to-boundary)
    # Query 2 neighbours; for room points the first hit is itself (dist=0), skip it.
    room_tree = KDTree(room_xy)
    if n > 1:
        rr_dists, _ = room_tree.query(room_xy, k=2)
        min_rr = rr_dists[:, 1]  # skip self (distance 0)
    else:
        min_rr = np.full(n, np.inf)

    boundary_tree = KDTree(boundary_xy)
    rb_dists, _ = boundary_tree.query(room_xy, k=1)
    min_rb = rb_dists

    nnd_array = np.minimum(min_rr, min_rb)
    mean_nnd = float(np.mean(nnd_array))
    std_nnd = float(np.std(nnd_array))

    # Uniformity: low std-dev relative to mean → score near 100
    exponent = max(-std_nnd / POINT_SPREAD_DISCREPANCY, -10.0)
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

    A SPATIAL_COVERAGE_ZONE_GRID_SCALE × SPATIAL_COVERAGE_ZONE_GRID_SCALE
    grid of probe points is generated across the floor plan.  For each probe
    the distance to the nearest room point is found.  The maximum of those
    distances is the "worst-case void size".  We normalise it against the
    theoretical ideal spacing (√(area / n)) so that adding more, well-spread
    rooms always improves the score.

    Optuna should minimise this penalty (high gap → low score).

    Returns (score_0_100, debug_dict).
    """
    g = SPATIAL_COVERAGE_ZONE_GRID_SCALE
    n = len(room_points)

    # Build probe grid
    xs = np.linspace(0.0, floor_width, g, dtype=np.float64)
    ys = np.linspace(0.0, floor_height, g, dtype=np.float64)
    gx, gy = np.meshgrid(xs, ys)
    probe_xy = np.column_stack([gx.ravel(), gy.ravel()])  # (g*g, 2)

    room_xy = np.array([(p.x, p.y) for p in room_points], dtype=np.float64)
    room_tree = KDTree(room_xy)

    probe_dists, _ = room_tree.query(probe_xy, k=1)

    max_gap = float(np.max(probe_dists))
    mean_gap = float(np.mean(probe_dists))

    # Normalise by ideal distance: score = 1 - (max_gap / ideal)  clamped [0,1]
    floor_area = floor_width * floor_height
    ideal_distance = math.sqrt(floor_area / n) if n > 0 else 1.0
    normalised_gap = max_gap / max(ideal_distance, 1e-9)
    score = float(np.clip((1.0 - normalised_gap) * 100.0, 0.0, 100.0))

    return score, {
        "grid_scale": g,
        "max_gap": max_gap,
        "mean_gap": mean_gap,
        "ideal_distance_grid": ideal_distance,
        "normalised_gap": normalised_gap,
        "probe_dists": probe_dists.reshape(g, g).tolist(),
        "probe_xy": probe_xy.tolist(),
    }


# ---------------------------------------------------------------------------
# Plotter
# ---------------------------------------------------------------------------


def _save_spatial_coverage_heatmap(
    room_points: list[OptunaScorePoint],
    requirements: FpgRequirements,
    scoring_details: dict[str, Any],
) -> None:
    """
    Save an enhanced spatial coverage visualisation with:
      - Gap heat-map (grid probe distances as a colour field)
      - Room points with NND circles
      - Score breakdown text panel
    """
    # Early-exit: only create/save plots when the final score is above the
    # configured threshold percentage of the section max score. This avoids
    # producing many low-value images during bulk runs/Optuna trials.
    final_score = scoring_details.get("final_score", 0.0)
    max_sc = scoring_details.get("max_score", max_score_limit)
    pct = (final_score / max_sc * 100.0) if max_sc else 0.0
    if pct < PLOT_THRESHOLD_PERCENT:
        # Lightweight log so users know why no plot was produced.
        print(
            f"[Info] Spatial coverage {pct:.1f}% below {PLOT_THRESHOLD_PERCENT}%, skipping heatmap."
        )
        return

    try:
        HEATMAP_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        floor_width = requirements.config.floor_plan_width
        floor_height = requirements.config.floor_plan_height

        # ── layout ──────────────────────────────────────────────────────────
        fig = plt.figure(figsize=(13.5, 9), facecolor="#f8f9fb")
        gs = fig.add_gridspec(
            1,
            2,
            width_ratios=[3.3, 0.95],
            left=0.05,
            right=0.97,
            top=0.88,
            bottom=0.08,
            wspace=0.04,
        )
        ax_map = fig.add_subplot(gs[0])
        ax_info = fig.add_subplot(gs[1])

        for ax in (ax_map, ax_info):
            ax.set_facecolor("white")
            for spine in ax.spines.values():
                spine.set_edgecolor("#b8c0cc")

        # ── gap heat-map ─────────────────────────────────────────────────────
        probe_dists_2d = scoring_details.get("probe_dists")
        if probe_dists_2d is not None:
            arr = np.array(probe_dists_2d, dtype=np.float64)
            cmap = mcolors.LinearSegmentedColormap.from_list(
                "gap_cmap",
                ["#1d4ed8", "#60a5fa", "#f8fafc", "#fca5a5", "#dc2626"],
            )
            im = ax_map.imshow(
                arr,
                origin="lower",
                extent=(0.0, float(floor_width), 0.0, float(floor_height)),
                cmap=cmap,
                aspect="auto",
                alpha=0.86,
                interpolation="bilinear",
                zorder=1,
            )
            cbar = fig.colorbar(im, ax=ax_map, fraction=0.02, pad=0.01)
            cbar.set_label(
                "Distance to nearest room point", color="#374151", fontsize=8
            )
            cbar.ax.yaxis.set_tick_params(color="#4b5563")
            plt.setp(cbar.ax.yaxis.get_ticklabels(), color="#4b5563", fontsize=7)
            cbar.ax.set_facecolor("white")

        # ── floor boundary ───────────────────────────────────────────────────
        boundary_rect = mpatches.FancyBboxPatch(
            (0, 0),
            floor_width,
            floor_height,
            boxstyle="square,pad=0",
            linewidth=1.8,
            edgecolor="#1f4e79",
            facecolor="none",
            zorder=2,
        )
        ax_map.add_patch(boundary_rect)

        # ── room points with NND radius ──────────────────────────────────────
        if room_points:
            room_xy = np.array([(p.x, p.y) for p in room_points])
            ideal_dist = scoring_details.get("ideal_distance", 0.0)
            nnd_arr = scoring_details.get("nnd_array", [])

            # NND radius circles (translucent)
            for i, p in enumerate(room_points):
                radius = nnd_arr[i] if i < len(nnd_arr) else ideal_dist
                circle = mpatches.Circle(
                    (p.x, p.y),
                    radius,
                    color="#f97316",
                    alpha=0.06,
                    linewidth=0,
                    zorder=3,
                )
                ax_map.add_patch(circle)

            # Ideal distance dashed ring on first point
            if ideal_dist > 0:
                ax_map.add_patch(
                    mpatches.Circle(
                        (room_points[0].x, room_points[0].y),
                        ideal_dist,
                        fill=False,
                        linestyle="--",
                        linewidth=1.2,
                        edgecolor="#16a34a",
                        alpha=0.7,
                        zorder=4,
                        label=f"Ideal Δ = {ideal_dist:.1f}",
                    )
                )

            # Room point scatter (use warm color to contrast blue heatmap)
            ax_map.scatter(
                room_xy[:, 0],
                room_xy[:, 1],
                s=150,
                c="#f97316",
                edgecolors="white",
                linewidths=1.5,
                zorder=6,
                label="Room Points",
            )

            # Labels
            # Annotations with subtle stroke for readability over heatmap
            for p in room_points:
                txt = ax_map.annotate(
                    p.name,
                    (p.x, p.y),
                    xytext=(6, 6),
                    textcoords="offset points",
                    fontsize=8,
                    color="#111827",
                    fontfamily="monospace",
                )
                txt.set_path_effects(
                    [patheffects.withStroke(linewidth=2.0, foreground="white")]
                )

        # ── axis cosmetics ───────────────────────────────────────────────────
        ax_map.set_xlim(-floor_width * 0.04, floor_width * 1.04)
        ax_map.set_ylim(-floor_height * 0.04, floor_height * 1.04)
        ax_map.set_aspect("equal")
        ax_map.grid(True, color="#d5dbe3", linewidth=0.7, linestyle=":")
        ax_map.tick_params(colors="#4b5563", labelsize=8)
        ax_map.set_xlabel("X  (floor width)", color="#374151", fontsize=9)
        ax_map.set_ylabel("Y  (floor height)", color="#374151", fontsize=9)
        ax_map.legend(
            loc="lower right",
            fontsize=8,
            framealpha=0.75,
            facecolor="white",
            edgecolor="#cfd6df",
            labelcolor="#374151",
            handlelength=0.8,
            handletextpad=0.5,
            borderpad=0.35,
            markerscale=1.0,
        )

        # ── title ────────────────────────────────────────────────────────────
        final_score = scoring_details.get("final_score", 0.0)
        max_sc = scoring_details.get("max_score", max_score_limit)
        pct = final_score / max_sc * 100 if max_sc else 0.0
        fig.suptitle(
            f"Spatial Coverage  ·  {final_score:.2f} / {max_sc}  ({pct:.0f}%)",
            fontsize=13,
            fontweight="semibold",
            color="#111827",
            y=0.95,
        )

        # ── info panel ───────────────────────────────────────────────────────
        ax_info.axis("off")

        nnd_score_100 = scoring_details.get("nnd_score_100", 0.0)
        grid_score_100 = scoring_details.get("grid_score_100", 0.0)
        mean_nnd = scoring_details.get("mean_nnd", 0.0)
        std_nnd = scoring_details.get("std_nnd", 0.0)
        max_gap = scoring_details.get("max_gap", 0.0)
        mean_gap = scoring_details.get("mean_gap", 0.0)
        norm_gap = scoring_details.get("normalised_gap", 0.0)
        n_pts = scoring_details.get("num_room_points", 0)
        area = scoring_details.get("floor_area", 0.0)
        ideal = scoring_details.get("ideal_distance", 0.0)
        grid_sc = scoring_details.get("grid_scale", SPATIAL_COVERAGE_ZONE_GRID_SCALE)

        def _bar(score_100: float, label: str, color: str) -> str:
            filled = int(round(score_100 / 10))
            bar = "█" * filled + "░" * (10 - filled)
            return f"{label}\n{bar}  {score_100:.1f}%"

        # --- Render info panel as two-column layout (label | value) ---
        ax_info.set_xlim(0, 1)
        ax_info.set_ylim(0, 1)

        left_x = 0.04
        right_x = 0.72
        y = 0.96
        line_height = 0.055

        label_box = dict(
            boxstyle="round,pad=0.18",
            facecolor="#ffffff",
            edgecolor="#eef2f6",
            alpha=0.95,
        )
        value_box = dict(
            boxstyle="round,pad=0.14",
            facecolor="#fcfdff",
            edgecolor="#f1f5f9",
            alpha=0.75,
        )

        # Header
        ax_info.text(
            left_x,
            y,
            "SCORE BREAKDOWN",
            transform=ax_info.transAxes,
            fontsize=11,
            color="#111827",
            fontweight="bold",
            verticalalignment="top",
            bbox=dict(facecolor="none", edgecolor="none", pad=0),
        )
        y -= line_height

        # Final score row (label + value)
        ax_info.text(
            left_x,
            y,
            "Final :",
            transform=ax_info.transAxes,
            fontsize=8,
            color="#374151",
            verticalalignment="top",
            bbox=label_box,
        )
        ax_info.text(
            right_x,
            y,
            f"{final_score:.3f} / {max_sc}",
            transform=ax_info.transAxes,
            fontsize=8,
            color="#374151",
            verticalalignment="top",
            fontfamily="monospace",
            bbox=value_box,
        )
        y -= line_height * 0.9

        # small separator
        ax_info.plot(
            [left_x, 0.96],
            [y + 0.01, y + 0.01],
            transform=ax_info.transAxes,
            color="#e6e9ee",
            linewidth=0.8,
        )
        y -= line_height * 0.18

        # NND section
        ax_info.text(
            left_x,
            y,
            "NND  (anti-clump)  40%",
            transform=ax_info.transAxes,
            fontsize=9,
            color="#1f4e79",
            fontweight="bold",
            verticalalignment="top",
        )
        y -= line_height * 0.88
        ax_info.text(
            left_x + 0.02,
            y,
            "Score:",
            transform=ax_info.transAxes,
            fontsize=8,
            color="#374151",
            verticalalignment="top",
            bbox=label_box,
        )
        ax_info.text(
            right_x,
            y,
            f"{nnd_score_100:.1f} / 100",
            transform=ax_info.transAxes,
            fontsize=8,
            color="#374151",
            verticalalignment="top",
            fontfamily="monospace",
            bbox=value_box,
        )
        y -= line_height * 0.78
        ax_info.text(
            left_x + 0.02,
            y,
            "Mean Δ:",
            transform=ax_info.transAxes,
            fontsize=8,
            color="#374151",
            verticalalignment="top",
            bbox=label_box,
        )
        ax_info.text(
            right_x,
            y,
            f"{mean_nnd:.2f}",
            transform=ax_info.transAxes,
            fontsize=8,
            color="#374151",
            verticalalignment="top",
            fontfamily="monospace",
            bbox=value_box,
        )
        y -= line_height * 0.78
        ax_info.text(
            left_x + 0.02,
            y,
            "Std Δ:",
            transform=ax_info.transAxes,
            fontsize=8,
            color="#374151",
            verticalalignment="top",
            bbox=label_box,
        )
        ax_info.text(
            right_x,
            y,
            f"{std_nnd:.2f}",
            transform=ax_info.transAxes,
            fontsize=8,
            color="#374151",
            verticalalignment="top",
            fontfamily="monospace",
            bbox=value_box,
        )
        y -= line_height * 0.9

        # GRID section
        ax_info.text(
            left_x,
            y,
            "GRID  (anti-gap)  60%",
            transform=ax_info.transAxes,
            fontsize=9,
            color="#8b5cf6",
            fontweight="bold",
            verticalalignment="top",
        )
        y -= line_height * 0.88
        ax_info.text(
            left_x + 0.02,
            y,
            "Scale:",
            transform=ax_info.transAxes,
            fontsize=8,
            color="#374151",
            verticalalignment="top",
            bbox=label_box,
        )
        ax_info.text(
            right_x,
            y,
            f"{grid_sc}×{grid_sc}",
            transform=ax_info.transAxes,
            fontsize=8,
            color="#374151",
            verticalalignment="top",
            fontfamily="monospace",
            bbox=value_box,
        )
        y -= line_height * 0.78
        ax_info.text(
            left_x + 0.02,
            y,
            "Score:",
            transform=ax_info.transAxes,
            fontsize=8,
            color="#374151",
            verticalalignment="top",
            bbox=label_box,
        )
        ax_info.text(
            right_x,
            y,
            f"{grid_score_100:.1f} / 100",
            transform=ax_info.transAxes,
            fontsize=8,
            color="#374151",
            verticalalignment="top",
            fontfamily="monospace",
            bbox=value_box,
        )
        y -= line_height * 0.78
        ax_info.text(
            left_x + 0.02,
            y,
            "Max gap:",
            transform=ax_info.transAxes,
            fontsize=8,
            color="#374151",
            verticalalignment="top",
            bbox=label_box,
        )
        ax_info.text(
            right_x,
            y,
            f"{max_gap:.2f}",
            transform=ax_info.transAxes,
            fontsize=8,
            color="#374151",
            verticalalignment="top",
            fontfamily="monospace",
            bbox=value_box,
        )
        y -= line_height * 0.78
        ax_info.text(
            left_x + 0.02,
            y,
            "Avg gap:",
            transform=ax_info.transAxes,
            fontsize=8,
            color="#374151",
            verticalalignment="top",
            bbox=label_box,
        )
        ax_info.text(
            right_x,
            y,
            f"{mean_gap:.2f}",
            transform=ax_info.transAxes,
            fontsize=8,
            color="#374151",
            verticalalignment="top",
            fontfamily="monospace",
            bbox=value_box,
        )
        y -= line_height * 0.78
        ax_info.text(
            left_x + 0.02,
            y,
            "Norm gap:",
            transform=ax_info.transAxes,
            fontsize=8,
            color="#374151",
            verticalalignment="top",
            bbox=label_box,
        )
        ax_info.text(
            right_x,
            y,
            f"{norm_gap:.3f}",
            transform=ax_info.transAxes,
            fontsize=8,
            color="#374151",
            verticalalignment="top",
            fontfamily="monospace",
            bbox=value_box,
        )
        y -= line_height * 0.9

        # separator
        ax_info.plot(
            [left_x, 0.96],
            [y + 0.02, y + 0.02],
            transform=ax_info.transAxes,
            color="#e6e9ee",
            linewidth=0.8,
        )
        y -= line_height * 0.18

        # GEOMETRY
        ax_info.text(
            left_x,
            y,
            "GEOMETRY",
            transform=ax_info.transAxes,
            fontsize=9,
            color="#111827",
            fontweight="bold",
            verticalalignment="top",
        )
        y -= line_height * 0.88
        ax_info.text(
            left_x + 0.02,
            y,
            "Points:",
            transform=ax_info.transAxes,
            fontsize=8,
            color="#374151",
            verticalalignment="top",
            bbox=label_box,
        )
        ax_info.text(
            right_x,
            y,
            f"{n_pts}",
            transform=ax_info.transAxes,
            fontsize=8,
            color="#374151",
            verticalalignment="top",
            fontfamily="monospace",
            bbox=value_box,
        )
        y -= line_height * 0.78
        ax_info.text(
            left_x + 0.02,
            y,
            "Area:",
            transform=ax_info.transAxes,
            fontsize=8,
            color="#374151",
            verticalalignment="top",
            bbox=label_box,
        )
        ax_info.text(
            right_x,
            y,
            f"{area:.1f}",
            transform=ax_info.transAxes,
            fontsize=8,
            color="#374151",
            verticalalignment="top",
            fontfamily="monospace",
            bbox=value_box,
        )
        y -= line_height * 0.78
        ax_info.text(
            left_x + 0.02,
            y,
            "Ideal Δ:",
            transform=ax_info.transAxes,
            fontsize=8,
            color="#374151",
            verticalalignment="top",
            bbox=label_box,
        )
        ax_info.text(
            right_x,
            y,
            f"{ideal:.2f}",
            transform=ax_info.transAxes,
            fontsize=8,
            color="#374151",
            verticalalignment="top",
            fontfamily="monospace",
            bbox=value_box,
        )

        # ── save ─────────────────────────────────────────────────────────────
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        plt.savefig(
            HEATMAP_OUTPUT_DIR / f"spatial_{timestamp}.png",
            dpi=120,
            bbox_inches="tight",
            facecolor=fig.get_facecolor(),
        )

    except Exception as e:
        print(f"[Warning] Failed to save spatial coverage heatmap: {e}")
    finally:
        plt.close("all")


# ---------------------------------------------------------------------------
# Public scoring function
# ---------------------------------------------------------------------------


def score_spatial_coverage(
    requirements: FpgRequirements, room_points: list[OptunaScorePoint]
) -> SectionScore:
    """
    Score spatial coverage by combining:
      • NND uniformity  (40%) — prevents point clumping
      • Grid-Sampling   (60%) — prevents voids / gaps across the floor plan

    Optuna should maximise this value (higher = better coverage).
    """
    warnings: list[str] = []

    floor_width = requirements.config.floor_plan_width
    floor_height = requirements.config.floor_plan_height
    floor_area = floor_width * floor_height

    if not room_points:
        warnings.append("No room points provided; spatial coverage score is 0.")
        details: dict[str, Any] = {
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
        _save_spatial_coverage_heatmap(room_points, requirements, details)
        return SectionScore(0.0, max_score_limit, details, warnings)

    # ── sub-scores ────────────────────────────────────────────────────────
    nnd_score_100, nnd_debug = _calculate_nnd_score(
        room_points, floor_width, floor_height
    )
    grid_score_100, grid_debug = _calculate_grid_sampling_score(
        room_points, floor_width, floor_height
    )

    # ── combine ───────────────────────────────────────────────────────────
    combined_100 = (NND_WEIGHT * nnd_score_100) + (GRID_WEIGHT * grid_score_100)
    combined_100 = float(np.clip(combined_100, 0.0, 100.0))

    # Map 0-100 → 0-max_score_limit
    final_score = normalize_section_score(
        combined_100 / 100.0 * max_score_limit, max_score_limit
    )

    # ── warnings ──────────────────────────────────────────────────────────
    if nnd_debug["std_nnd"] > nnd_debug["ideal_distance"] * 2.0:
        warnings.append(
            f"High NND std-dev ({nnd_debug['std_nnd']:.2f}) → irregular clustering."
        )
    if grid_debug["normalised_gap"] > 1.5:
        warnings.append(
            f"Large void detected: max_gap={grid_debug['max_gap']:.2f} "
            f"({grid_debug['normalised_gap']:.2f}× ideal spacing)."
        )

    # ── build details dict ────────────────────────────────────────────────
    scoring_details: dict[str, Any] = {
        "final_score": final_score,
        "max_score": max_score_limit,
        "combined_100": combined_100,
        "nnd_score_100": nnd_score_100,
        "grid_score_100": grid_score_100,
        "nnd_weight": NND_WEIGHT,
        "grid_weight": GRID_WEIGHT,
        # NND
        "mean_nnd": nnd_debug["mean_nnd"],
        "std_nnd": nnd_debug["std_nnd"],
        "ideal_distance": nnd_debug["ideal_distance"],
        "nnd_array": nnd_debug["nnd_array"],
        # Grid
        "grid_scale": grid_debug["grid_scale"],
        "max_gap": grid_debug["max_gap"],
        "mean_gap": grid_debug["mean_gap"],
        "normalised_gap": grid_debug["normalised_gap"],
        "ideal_distance_grid": grid_debug["ideal_distance_grid"],
        "probe_dists": grid_debug["probe_dists"],
        # Geometry
        "num_room_points": len(room_points),
        "floor_area": floor_area,
    }

    _save_spatial_coverage_heatmap(room_points, requirements, scoring_details)

    return SectionScore(final_score, max_score_limit, scoring_details, warnings)

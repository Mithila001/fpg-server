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

from app.algorithms.fpg_optuna_score.util.scoring_common import OptunaScorePoint
from app.algorithms.types.domain import FpgRequirements
from app.core.fpg_rooms.config_fpg import OPTUNA_SCORING_VALUES


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
PLOT_THRESHOLD_PERCENT = 60


max_score_limit = OPTUNA_SCORING_VALUES.get("optuna_score_spatial_coverage", 0)


def save_spatial_coverage_heatmap(
    room_points: list[OptunaScorePoint],
    requirements: FpgRequirements,
    scoring_details: dict[str, Any],
) -> None:
    final_score = scoring_details.get("final_score", 0.0)
    max_sc = scoring_details.get("max_score", max_score_limit)
    pct = (final_score / max_sc * 100.0) if max_sc else 0.0

    if pct < PLOT_THRESHOLD_PERCENT:
        print(
            f"[Info] Spatial coverage {pct:.1f}% below {PLOT_THRESHOLD_PERCENT}%, skipping heatmap."
        )
        return

    try:
        HEATMAP_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        floor_width = requirements.config.floor_plan_width
        floor_height = requirements.config.floor_plan_height

        # --- FIX 1: Initialize variables at the top to prevent "unbound" errors ---
        ideal_radius = scoring_details.get("theoretical_min_max_gap", 0.0)
        num_points = len(room_points)

        fig = plt.figure(figsize=(14, 8), facecolor="#ffffff")
        gs = fig.add_gridspec(
            1, 2, width_ratios=[3, 1], left=0.05, right=0.95, wspace=0.1
        )
        ax_map = fig.add_subplot(gs[0])
        ax_info = fig.add_subplot(gs[1])

        ax_map.set_facecolor("#fcfcfc")

        # ── Gap Heatmap ──────────────────────────────────────────────────────
        probe_dists_2d = scoring_details.get("probe_dists")
        if probe_dists_2d is not None:
            arr = np.array(probe_dists_2d, dtype=np.float64)
            cmap = mcolors.LinearSegmentedColormap.from_list(
                "gap_cmap", ["#0ea5e9", "#f0f9ff", "#fee2e2", "#ef4444"]
            )
            im = ax_map.imshow(
                arr,
                origin="lower",
                extent=(0.0, float(floor_width), 0.0, float(floor_height)),
                cmap=cmap,
                aspect="equal",
                alpha=0.8,
                interpolation="bilinear",
                zorder=1,
            )
            cbar = fig.colorbar(im, ax=ax_map, fraction=0.03, pad=0.02)
            cbar.outline.set_visible(False)  # type: ignore
            cbar.ax.tick_params(labelsize=7)

        # ── Floor Boundary ───────────────────────────────────────────────────
        ax_map.add_patch(
            mpatches.Rectangle(
                (0, 0),
                floor_width,
                floor_height,
                linewidth=2,
                edgecolor="#334155",
                facecolor="none",
                zorder=5,
            )
        )

        # ── Room Points ──────────────────────────────────────────────────────
        if room_points:
            room_xy = np.array([(p.x, p.y) for p in room_points])

            ax_map.scatter(
                room_xy[:, 0],
                room_xy[:, 1],
                s=120,
                c="#1e293b",
                edgecolors="white",
                linewidths=1.5,
                zorder=10,
                label="Room Centers",
            )

            for p in room_points:
                # Use the ideal radius for the halos
                ax_map.add_patch(
                    mpatches.Circle(
                        (p.x, p.y),
                        ideal_radius,
                        color="#0ea5e9",
                        alpha=0.1,
                        linewidth=0,
                        zorder=2,
                    )
                )

                txt = ax_map.text(
                    p.x,
                    p.y + (floor_height * 0.02),
                    p.name,
                    fontsize=7,
                    fontweight="bold",
                    ha="center",
                    zorder=11,
                )
                txt.set_path_effects(
                    [patheffects.withStroke(linewidth=2, foreground="white")]
                )

        # ── Map Cosmetics ────────────────────────────────────────────────────
        ax_map.set_xlim(-floor_width * 0.05, floor_width * 1.05)
        ax_map.set_ylim(-floor_height * 0.05, floor_height * 1.05)

        # --- FIX 2: Avoid Spine looping issue by using axis("off") or explicit sets ---
        ax_map.axis("off")
        ax_info.axis("off")

        # ── Clean Info Panel (No Boxes/Overdue Style) ────────────────────────
        y_pos = 0.95

        def _write(text, x=0, size=9, color="#1e293b", weight="normal"):
            nonlocal y_pos
            ax_info.text(
                x,
                y_pos,
                text,
                transform=ax_info.transAxes,
                fontsize=size,
                color=color,
                fontweight=weight,
                va="top",
            )
            y_pos -= 0.045

        _write("SPATIAL METRICS", size=12, weight="bold", color="#0f172a")
        y_pos -= 0.02

        _write(f"Final Score: {final_score:.2f} / {max_sc}", weight="bold")
        _write(f"Efficiency: {pct:.1f}%", color="#0284c7" if pct > 70 else "#b91c1c")
        y_pos -= 0.03

        _write("CLUSTERING (NND)", weight="bold", color="#475569")
        _write(f"• Score: {scoring_details.get('nnd_score_100', 0.0):.1f}/100")
        cv = scoring_details.get("std_nnd", 0.0) / max(
            scoring_details.get("mean_nnd", 1e-9), 1e-9
        )
        _write(f"• Variation (CV): {cv:.3f}")
        y_pos -= 0.03

        _write("COVERAGE (GRID)", weight="bold", color="#475569")
        g_scale = scoring_details.get("grid_scale", SPATIAL_COVERAGE_ZONE_GRID_SCALE)
        _write(f"• Resolution: {g_scale} x {g_scale}")
        _write(f"• Max Gap: {scoring_details.get('max_gap', 0.0):.2f}m")
        _write(f"• Norm Ratio: {scoring_details.get('normalised_gap', 0.0):.2f}x")
        y_pos -= 0.03

        _write("GEOMETRY", weight="bold", color="#475569")
        _write(f"• Points: {num_points}")
        _write(f"• Area: {scoring_details.get('floor_area', 0.0):.1f} m²")
        _write(f"• Ideal Radius: {ideal_radius:.2f}m")  # No longer unbound

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plt.savefig(
            HEATMAP_OUTPUT_DIR / f"spatial_{timestamp}.png",
            dpi=130,
            bbox_inches="tight",
        )

    except Exception as e:
        print(f"[Warning] Failed to save spatial coverage heatmap: {e}")
    finally:
        plt.close("all")

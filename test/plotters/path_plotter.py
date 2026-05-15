"""Path simulation plotters.

Provides two outputs:
1) A meaningful 4-panel score visual summary.
2) A dedicated path-only multi-panel grid (one path per subplot).
"""

from __future__ import annotations

import os
import math
from datetime import datetime
from typing import Any, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon, Rectangle
import numpy as np
from scipy import ndimage

from app.algorithms.fgp_score.score_functional.path_simulations import (
    path_sim_config,
)
from app.algorithms.fgp_score.score_functional.path_simulations.util.pathfinder import (
    ROOM_TYPE_CODES,
)
from app.algorithms.fgp_score.score_functional.path_simulations.types import (
    PathScoreResult,
)

# ---------------------------------------------------------------------------
# Theme (light classic - from config)
# ---------------------------------------------------------------------------

_BG = path_sim_config.PLOT_BG_COLOR
_PANEL_BG = path_sim_config.PLOT_PANEL_BG_COLOR
_TEXT = path_sim_config.PLOT_TEXT_COLOR
_GRID = path_sim_config.PLOT_GRID_COLOR
_ROOM_COLORS = path_sim_config.PLOT_ROOM_COLORS
_DEFAULT_ROOM = path_sim_config.PLOT_DEFAULT_ROOM_COLOR

_LIVING_CODE = ROOM_TYPE_CODES["livingRoom"]
_KITCHEN_CODE = ROOM_TYPE_CODES["kitchen"]
_BEDROOM_CODE = ROOM_TYPE_CODES["bedroom"]
_HALLWAY_CODE = ROOM_TYPE_CODES["hallway"]
_BATHROOM_CODES = {ROOM_TYPE_CODES["bathroom"], ROOM_TYPE_CODES["attachedBathroom"]}

PRIVACY_RADIUS_CM = path_sim_config.PRIVACY_RADIUS_CM


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _default_output_dir() -> str:
    """Returns absolute path to fpg-server/test/outputs/score/path_sim_score."""
    here = os.path.dirname(__file__)
    return os.path.abspath(
        os.path.join(
            here,
            "..",  # Up to 'test'
            "outputs",
            "score",
            "path_sim_score",
        )
    )


def _path_only_output_dir(base_output_dir: str) -> str:
    return os.path.join(base_output_dir, "path_only")


def _timestamped_png_path(output_dir: str) -> str:
    now = datetime.now()
    ms = now.microsecond // 1000
    fname = now.strftime(f"%Y-%m-%d-%H-%M-%S-{ms:03d}") + ".png"
    return os.path.join(output_dir, fname)


def _draw_rooms(ax: Any, rooms: List[Any]) -> None:
    """Draw filled room polygons on ax."""
    for room in rooms:
        verts = _get(room, "vertices", [])
        if not verts or len(verts) < 3:
            continue
        rtype = str(_get(room, "type", ""))
        color = _ROOM_COLORS.get(rtype, _DEFAULT_ROOM)
        patch = MplPolygon(
            verts,
            closed=True,
            facecolor=color,
            edgecolor="#7a7a7a",
            linewidth=0.8,
            alpha=0.85,
        )
        ax.add_patch(patch)


def _set_ax_style(ax: Any, title: str, rooms: List[Any]) -> None:
    """Set axis styling and bounds based on room coordinates."""
    ax.set_facecolor(_PANEL_BG)
    ax.set_title(title, color=_TEXT, fontsize=8, pad=5, weight="bold")
    ax.tick_params(colors=_TEXT, labelsize=5)
    ax.grid(True, color=_GRID, linewidth=0.4, alpha=0.6)
    for spine in ax.spines.values():
        spine.set_edgecolor("#b9b3a8")
        spine.set_linewidth(0.6)

    all_x: List[float] = []
    all_y: List[float] = []
    for room in rooms:
        for v in _get(room, "vertices", []):
            all_x.append(v[0])
            all_y.append(v[1])
    if all_x:
        pad = 20.0
        ax.set_xlim(min(all_x) - pad, max(all_x) + pad)
        ax.set_ylim(min(all_y) - pad, max(all_y) + pad)
    ax.set_aspect("equal", adjustable="box")


def _plot_all_paths_overlay(ax: Any, result: PathScoreResult) -> None:
    for path in result.paths:
        if len(path.coords) < 2:
            continue
        xs = [c[0] for c in path.coords]
        ys = [c[1] for c in path.coords]
        ax.plot(xs, ys, color=path.color, linewidth=1.4, alpha=0.9, zorder=5)


def _score_bars(ax: Any, result: PathScoreResult) -> None:
    labels = ["Circ.", "Privacy", "Hallway", "Furniture"]
    values = [
        result.circulation_efficiency,
        result.privacy_score,
        result.hallway_utility,
        result.furniture_flexibility,
    ]
    colors = ["#e07a5f", "#3d5a80", "#2a9d8f", "#f4a261"]
    y = np.arange(len(labels))

    ax.barh(y, values, color=colors, alpha=0.9)
    ax.set_yticks(y, labels=labels)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Score")
    ax.invert_yaxis()
    for i, v in enumerate(values):
        ax.text(min(v + 1.5, 98), i, f"{v:.1f}", va="center", ha="left", fontsize=7)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def save_path_score_plot(
    grid: Any,
    result: PathScoreResult,
    rooms: List[Any],
    output_dir: str | None = None,
) -> str:
    """Save meaningful 4-panel score PNG and return absolute file path."""
    output_dir = output_dir or _default_output_dir()
    os.makedirs(output_dir, exist_ok=True)

    save_path = _timestamped_png_path(output_dir)

    fig, (ax1, ax2, ax3, ax4) = plt.subplots(
        1, 4, figsize=(28, 7), dpi=120, facecolor=_BG
    )
    fig.suptitle(
        f"Path Simulation Scoring  |  Total: {result.total_score:.1f}  "
        f"| Circ: {result.circulation_efficiency:.1f}  "
        f"Priv: {result.privacy_score:.1f}  "
        f"Hall: {result.hallway_utility:.1f}  "
        f"Furn: {result.furniture_flexibility:.1f}",
        color=_TEXT,
        fontsize=10,
        weight="bold",
        y=0.98,
    )

    # PANEL 1: All paths + quick score bars
    _draw_rooms(ax1, rooms)
    _set_ax_style(ax1, "1) All Simulated Paths", rooms)
    _plot_all_paths_overlay(ax1, result)
    ax1.text(
        0.02,
        0.02,
        f"Total={result.total_score:.1f} | Paths={len(result.paths)}",
        transform=ax1.transAxes,
        va="bottom",
        ha="left",
        fontsize=7,
        color=_TEXT,
        weight="bold",
        bbox={"facecolor": "#ffffff", "alpha": 0.9, "edgecolor": "#c7c1b6"},
    )

    # PANEL 2: Circulation traffic + bars
    _draw_rooms(ax2, rooms)
    _set_ax_style(ax2, "2) Circulation Heat + Score Bars", rooms)

    if (
        grid.walkable is not None
        and grid.room_type_grid is not None
        and grid.traffic_map is not None
    ):
        res = grid.resolution
        min_x, min_y, _, _ = grid.bounds
        h, w = grid.height, grid.width

        for iy in range(h):
            for ix in range(w):
                if not grid.walkable[iy, ix]:
                    continue
                if not (
                    (grid.room_type_grid[iy, ix] == _LIVING_CODE)
                    or (grid.room_type_grid[iy, ix] == _KITCHEN_CODE)
                ):
                    continue
                cx = min_x + (ix + 0.5) * res
                cy = min_y + (iy + 0.5) * res
                intensity = grid.traffic_map[iy, ix] / max(
                    1.0, np.max(grid.traffic_map)
                )
                color_val = int(100 - 100 * intensity)
                rect = Rectangle(
                    (cx - res / 2, cy - res / 2),
                    res,
                    res,
                    facecolor=f"#{255:02x}{color_val:02x}00",
                    edgecolor="none",
                    alpha=0.3 + 0.4 * intensity,
                    zorder=4,
                )
                ax2.add_patch(rect)

    inset = ax2.inset_axes([0.60, 0.05, 0.38, 0.40])
    inset.set_facecolor("#ffffff")
    _score_bars(inset, result)
    inset.tick_params(labelsize=6)

    # PANEL 3: Privacy Score (bedroom zones and breach visualization)
    _draw_rooms(ax3, rooms)
    _set_ax_style(ax3, "3) Privacy Zones + Breaches", rooms)

    if (
        grid.walkable is not None
        and grid.room_type_grid is not None
        and grid.traffic_map is not None
    ):
        res = grid.resolution
        min_x, min_y, _, _ = grid.bounds
        h, w = grid.height, grid.width

        # Extract bedroom door points from paths
        bedroom_doors = []
        for path in result.paths:
            for x, y in path.coords:
                if path.is_public:
                    continue
                for room in rooms:
                    if _get(room, "type", "") == "bedroom":
                        verts = _get(room, "vertices", [])
                        xs = [v[0] for v in verts]
                        ys = [v[1] for v in verts]
                        if min(xs) <= x <= max(xs) and min(ys) <= y <= max(ys):
                            bedroom_doors.append((x, y))
                            break

        # Draw privacy zones (buffer around bedroom doors)
        privacy_cells = max(1, int(PRIVACY_RADIUS_CM / res))
        struct = ndimage.generate_binary_structure(2, 2)

        for bx, by in bedroom_doors:
            ix = int((bx - min_x) / res)
            iy = int((by - min_y) / res)
            ix = max(0, min(w - 1, ix))
            iy = max(0, min(h - 1, iy))

            # Create a small mask for this door
            door_mask = np.zeros((h, w), dtype=bool)
            door_mask[iy, ix] = True

            # Dilate to privacy buffer
            buffer_mask = ndimage.binary_dilation(
                door_mask, structure=struct, iterations=privacy_cells
            )

            # Draw buffer zones
            for idy in range(h):
                for idx in range(w):
                    if buffer_mask[idy, idx] and grid.walkable[idy, idx]:
                        cx = min_x + (idx + 0.5) * res
                        cy = min_y + (idy + 0.5) * res
                        rect = Rectangle(
                            (cx - res / 2, cy - res / 2),
                            res,
                            res,
                            facecolor="#90EE90",
                            edgecolor="none",
                            alpha=0.2,
                            zorder=4,
                        )
                        ax3.add_patch(rect)

        # Mark bedroom cells touched by traffic in red (privacy risk signal)
        for iy in range(h):
            for ix in range(w):
                if not grid.walkable[iy, ix]:
                    continue
                if grid.room_type_grid[iy, ix] != _BEDROOM_CODE:
                    continue
                if grid.traffic_map[iy, ix] > 0:
                    cx = min_x + (ix + 0.5) * res
                    cy = min_y + (iy + 0.5) * res
                    rect = Rectangle(
                        (cx - res / 2, cy - res / 2),
                        res,
                        res,
                        facecolor="#FF6B6B",
                        edgecolor="none",
                        alpha=0.5,
                        zorder=5,
                    )
                    ax3.add_patch(rect)

    ax3.text(
        0.02,
        0.02,
        f"Score: {result.privacy_score:.1f}",
        transform=ax3.transAxes,
        va="bottom",
        ha="left",
        fontsize=7,
        color=_TEXT,
        weight="bold",
        bbox={"facecolor": "#ffffff", "alpha": 0.9, "edgecolor": "#c7c1b6"},
    )

    # PANEL 4: Hallway + furniture map
    _draw_rooms(ax4, rooms)
    _set_ax_style(ax4, "4) Hallway Utility + Furniture Quiet Zones", rooms)

    if (
        grid.walkable is not None
        and grid.room_type_grid is not None
        and grid.traffic_map is not None
    ):
        res = grid.resolution
        min_x, min_y, _, _ = grid.bounds
        h, w = grid.height, grid.width

        for iy in range(h):
            for ix in range(w):
                if not grid.walkable[iy, ix]:
                    continue
                if grid.room_type_grid[iy, ix] != _HALLWAY_CODE:
                    continue
                cx = min_x + (ix + 0.5) * res
                cy = min_y + (iy + 0.5) * res
                used = grid.traffic_map[iy, ix] > 0
                color = "#66BB6A" if used else "#EF5350"
                rect = Rectangle(
                    (cx - res / 2, cy - res / 2),
                    res,
                    res,
                    facecolor=color,
                    edgecolor="none",
                    alpha=0.65,
                    zorder=7,
                )
                ax4.add_patch(rect)

        for iy in range(h):
            for ix in range(w):
                if not grid.walkable[iy, ix]:
                    continue
                if not (
                    (grid.room_type_grid[iy, ix] == _LIVING_CODE)
                    or (grid.room_type_grid[iy, ix] == _BEDROOM_CODE)
                ):
                    continue
                cx = min_x + (ix + 0.5) * res
                cy = min_y + (iy + 0.5) * res
                is_quiet = grid.traffic_map[iy, ix] == 0
                color = "#81C784" if is_quiet else "#FFB74D"
                rect = Rectangle(
                    (cx - res / 2, cy - res / 2),
                    res,
                    res,
                    facecolor=color,
                    edgecolor="none",
                    alpha=0.35 if is_quiet else 0.2,
                    zorder=4,
                )
                ax4.add_patch(rect)

    ax4.text(
        0.02,
        0.02,
        f"Hall={result.hallway_utility:.1f} | Furn={result.furniture_flexibility:.1f}",
        transform=ax4.transAxes,
        va="bottom",
        ha="left",
        fontsize=7,
        color=_TEXT,
        weight="bold",
        bbox={"facecolor": "#ffffff", "alpha": 0.9, "edgecolor": "#c7c1b6"},
    )

    # =====================================================================
    # Save figure
    # =====================================================================
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.96))
    fig.savefig(save_path, facecolor=_BG, dpi=120, bbox_inches="tight")
    plt.close(fig)

    return os.path.abspath(save_path)


def save_path_only_grid_plot(
    result: PathScoreResult,
    rooms: List[Any],
    output_dir: str | None = None,
) -> str:
    """Save path-only multi-panel grid (one simulation path per subplot)."""
    base_dir = output_dir or _default_output_dir()
    path_only_dir = _path_only_output_dir(base_dir)
    os.makedirs(path_only_dir, exist_ok=True)
    save_path = _timestamped_png_path(path_only_dir)

    num_paths = max(1, len(result.paths))
    cols = min(3, num_paths)
    rows = int(math.ceil(num_paths / cols))

    fig, axes = plt.subplots(
        rows,
        cols,
        figsize=(7.8 * cols, 5.6 * rows),
        dpi=120,
        facecolor=_BG,
    )

    axes_arr = np.atleast_1d(axes).ravel()

    for idx, ax in enumerate(axes_arr):
        if idx >= len(result.paths):
            ax.axis("off")
            continue

        path = result.paths[idx]
        _draw_rooms(ax, rooms)
        _set_ax_style(ax, f"Path {idx + 1}: {path.label}", rooms)

        if len(path.coords) >= 2:
            xs = [c[0] for c in path.coords]
            ys = [c[1] for c in path.coords]
            ax.plot(xs, ys, color=path.color, linewidth=2.1, alpha=0.95, zorder=6)
            ax.scatter(xs[0], ys[0], s=44, color="#1b4332", zorder=7, label="start")
            ax.scatter(xs[-1], ys[-1], s=44, color="#9d0208", zorder=7, label="end")

        ax.text(
            0.02,
            0.02,
            f"Type={'Public' if path.is_public else 'Private'} | Nodes={len(path.coords)}",
            transform=ax.transAxes,
            va="bottom",
            ha="left",
            fontsize=7,
            color=_TEXT,
            bbox={"facecolor": "#ffffff", "alpha": 0.88, "edgecolor": "#c7c1b6"},
        )

    fig.suptitle(
        f"Path-Only Simulation Grid | Total={result.total_score:.1f} | Paths={len(result.paths)}",
        color=_TEXT,
        fontsize=11,
        weight="bold",
        y=0.995,
    )
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.97))
    fig.savefig(save_path, facecolor=_BG, dpi=120, bbox_inches="tight")
    plt.close(fig)

    return os.path.abspath(save_path)

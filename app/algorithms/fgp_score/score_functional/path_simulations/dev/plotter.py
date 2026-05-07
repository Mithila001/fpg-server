"""3-panel debug plotter for path simulation.

Saves a single PNG with:
  Panel 1 – Floor plan + colour-coded simulated paths
  Panel 2 – Hallway utility (used=green, unused=red)
  Panel 3 – Traffic intensity heatmap

Output: test/outputs/score/critical_score/path_score/YYYY-MM-DD-HH-MM-SS-ms.png
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
import numpy as np
from shapely.geometry import Polygon

from ..pathfinder import ROOM_TYPE_CODES
from ..types import PathResult, PathScoreResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BG = "#121212"
_PANEL_BG = "#1a1a1a"
_TEXT = "#e0e0e0"

_HALLWAY_CODE = ROOM_TYPE_CODES["hallway"]

_ROOM_COLOURS = {
    "livingRoom":       "#3a5a4a",
    "bedroom":          "#2a3d5a",
    "kitchen":          "#3a4a2a",
    "bathroom":         "#2a4a5a",
    "attachedBathroom": "#1e3d52",
    "hallway":          "#4a3a5a",
    "diningRoom":       "#5a4a2a",
    "garage":           "#3a3a3a",
    "verandaOutdoorSpace": "#2e4a2e",
}
_DEFAULT_ROOM = "#2c2c2c"

_PATH_COLOURS = {
    "entry_kitchen":     "#FF6B35",
    "entry_bedroom":     "#4ECDC4",
    "entry_bathroom":    "#45B7D1",
    "bedroom_bathroom":  "#96CEB4",
    "bedroom_kitchen":   "#FFEAA7",
}


def _default_output_dir() -> str:
    here = os.path.dirname(__file__)
    return os.path.abspath(
        os.path.join(here, "..", "..", "..", "..", "..", "..",
                     "test", "outputs", "score", "critical_score", "path_score")
    )


def _draw_rooms(ax: Any, rooms: List[Any]) -> None:
    """Draw filled room polygons on ax."""
    for room in rooms:
        verts = getattr(room, "vertices", [])
        if not verts or len(verts) < 3:
            continue
        rtype = str(getattr(room, "type", ""))
        colour = _ROOM_COLOURS.get(rtype, _DEFAULT_ROOM)
        patch = MplPolygon(
            verts, closed=True,
            facecolor=colour, edgecolor="#555555",
            linewidth=0.8, alpha=0.85,
        )
        ax.add_patch(patch)
        # Label
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        name = str(getattr(room, "name", rtype))
        ax.text(cx, cy, name, ha="center", va="center",
                fontsize=5.5, color="#cccccc", alpha=0.8)


def _set_ax_style(ax: Any, title: str, rooms: List[Any]) -> None:
    ax.set_facecolor(_PANEL_BG)
    ax.set_title(title, color=_TEXT, fontsize=9, pad=6)
    ax.tick_params(colors=_TEXT, labelsize=6)
    for spine in ax.spines.values():
        spine.set_edgecolor("#444444")
    # Auto-bounds from rooms
    all_x: List[float] = []
    all_y: List[float] = []
    for room in rooms:
        for v in getattr(room, "vertices", []):
            all_x.append(v[0])
            all_y.append(v[1])
    if all_x:
        pad = 30.0
        ax.set_xlim(min(all_x) - pad, max(all_x) + pad)
        ax.set_ylim(min(all_y) - pad, max(all_y) + pad)
    ax.set_aspect("equal", adjustable="box")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save_path_score_plot(
    grid: Any,           # AStarGrid instance (post-rasterize + label)
    result: PathScoreResult,
    rooms: List[Any],
    output_dir: str | None = None,
) -> str:
    """Save 3-panel debug PNG, return absolute file path."""
    output_dir = output_dir or _default_output_dir()
    os.makedirs(output_dir, exist_ok=True)

    now = datetime.now()
    ms = now.microsecond // 1000
    fname = now.strftime(f"%Y-%m-%d-%H-%M-%S-{ms:03d}") + ".png"
    save_path = os.path.join(output_dir, fname)

    fig, (ax1, ax2, ax3) = plt.subplots(
        1, 3, figsize=(24, 9), dpi=150, facecolor=_BG
    )

    # ------------------------------------------------------------------
    # Panel 1 – Floor plan + paths
    # ------------------------------------------------------------------
    _draw_rooms(ax1, rooms)
    _set_ax_style(ax1, "Path Simulation  |  colour by route type", rooms)

    legend_handles: List[Any] = []
    seen_labels: set[str] = set()

    for path in result.paths:
        if len(path.coords) < 2:
            continue
        xs = [c[0] for c in path.coords]
        ys = [c[1] for c in path.coords]
        ax1.plot(xs, ys, color=path.color, linewidth=1.6, alpha=0.85, zorder=5)
        if path.label not in seen_labels:
            seen_labels.add(path.label)
            legend_handles.append(
                mpatches.Patch(color=path.color, label=path.label)
            )

    if legend_handles:
        ax1.legend(
            handles=legend_handles, loc="upper right",
            fontsize=5, framealpha=0.3,
            facecolor=_PANEL_BG, edgecolor="#444444",
            labelcolor=_TEXT,
        )

    # ------------------------------------------------------------------
    # Panel 2 – Hallway utility
    # ------------------------------------------------------------------
    _draw_rooms(ax2, rooms)
    _set_ax_style(ax2, "Hallway Utility  |  green=used  red=unused", rooms)

    if grid.walkable is not None and grid.room_type_grid is not None and grid.traffic_map is not None:
        res = grid.resolution
        min_x, min_y, _, _ = grid.bounds
        h, w = grid._height, grid._width

        for iy in range(h):
            for ix in range(w):
                if not grid.walkable[iy, ix]:
                    continue
                if grid.room_type_grid[iy, ix] != _HALLWAY_CODE:
                    continue
                cx = min_x + (ix + 0.5) * res
                cy = min_y + (iy + 0.5) * res
                used = grid.traffic_map[iy, ix] > 0
                colour = "#00c853" if used else "#d50000"
                rect = plt.Rectangle(
                    (cx - res / 2, cy - res / 2), res, res,
                    facecolor=colour, edgecolor="none", alpha=0.65, zorder=6
                )
                ax2.add_patch(rect)

    ax2.text(
        0.02, 0.98,
        f"Hallway Utility: {result.hallway_utility:.1f}/25",
        transform=ax2.transAxes, va="top", ha="left",
        fontsize=7, color=_TEXT,
        bbox={"facecolor": "#1e1e1e", "alpha": 0.8, "edgecolor": "#555"},
    )

    # ------------------------------------------------------------------
    # Panel 3 – Traffic heatmap
    # ------------------------------------------------------------------
    ax3.set_facecolor(_PANEL_BG)
    ax3.set_title("Traffic Intensity  |  bright=high traffic", color=_TEXT, fontsize=9, pad=6)
    ax3.tick_params(colors=_TEXT, labelsize=6)
    for spine in ax3.spines.values():
        spine.set_edgecolor("#444444")

    if grid.traffic_map is not None and grid.walkable is not None:
        # Mask obstacles as NaN for display
        display_map = np.where(grid.walkable, grid.traffic_map, np.nan)
        min_x_b, min_y_b, max_x_b, max_y_b = grid.bounds
        extent = [min_x_b, max_x_b, min_y_b, max_y_b]

        im = ax3.imshow(
            display_map,
            origin="lower",
            extent=extent,
            cmap="inferno",
            interpolation="nearest",
            aspect="equal",
        )
        cb = fig.colorbar(im, ax=ax3, fraction=0.03, pad=0.02)
        cb.ax.tick_params(colors=_TEXT, labelsize=6)
        cb.set_label("Path hits per cell", color=_TEXT, fontsize=7)

        # Overlay room outlines
        for room in rooms:
            verts = getattr(room, "vertices", [])
            if len(verts) < 3:
                continue
            xs = [v[0] for v in verts] + [verts[0][0]]
            ys = [v[1] for v in verts] + [verts[0][1]]
            ax3.plot(xs, ys, color="#555555", linewidth=0.6, alpha=0.6)

    ax3.set_aspect("equal", adjustable="box")

    # ------------------------------------------------------------------
    # Figure title with score summary
    # ------------------------------------------------------------------
    fig.suptitle(
        f"Path Simulation Score: {result.total_score:.1f}/100  |  "
        f"Circ={result.circulation_efficiency:.1f}  "
        f"Priv={result.privacy_score:.1f}  "
        f"Hall={result.hallway_utility:.1f}  "
        f"Furn={result.furniture_flexibility:.1f}",
        color=_TEXT, fontsize=10, y=0.995,
    )

    fig.tight_layout(rect=[0.0, 0.0, 1.0, 0.99])
    fig.savefig(save_path, facecolor=_BG, dpi=150)
    plt.close(fig)

    return os.path.abspath(save_path)

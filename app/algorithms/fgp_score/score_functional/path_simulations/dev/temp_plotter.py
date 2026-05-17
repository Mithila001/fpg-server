"""Professional multi-panel path simulation plotter.

Panels:
  - Main (large): Floor plan with smooth curved paths, door markers,
    and path-overlap regions highlighted in translucent red
  - Top-right: Hallway utility bar chart (used vs unused)
  - Bottom strip: Path legend + stats summary

No imports from outside this package.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np
from matplotlib.patches import FancyArrowPatch, Polygon as MplPolygon
from shapely.geometry import MultiPolygon, Polygon

from .. import path_sim_config
from ..util._dev_print import dev_print

_WorldPt = Tuple[float, float]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _room_centroid(room: Any) -> Optional[_WorldPt]:
    verts = _get(room, "vertices", [])
    if not verts or len(verts) < 3:
        return None
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def _room_label(room: Any) -> str:
    rtype = str(_get(room, "type", ""))
    replacements = {
        "attachedBathroom": "A.Bath",
        "verandaOutdoorSpace": "Veranda",
        "diningRoom": "Dining",
        "bedroom": "Bed",
        "kitchen": "Kit",
        "bathroom": "Bath",
        "hallway": "Hall",
        "livingRoom": "Living",
        "garage": "Garage",
        "veranda": "Veranda",
    }
    return replacements.get(rtype, rtype[:6] if rtype else "?")


def _timestamped_path(output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    now = datetime.now()
    ms = now.microsecond // 1000
    fname = now.strftime(f"%Y-%m-%d-%H-%M-%S-{ms:03d}") + "_paths.png"
    return os.path.join(output_dir, fname)


def _get_floor_bounds(rooms: List[Any], pad: float = 15.0) -> Tuple[float, float, float, float]:
    all_x, all_y = [], []
    for room in rooms:
        for v in _get(room, "vertices", []):
            all_x.append(v[0])
            all_y.append(v[1])
    if not all_x:
        return (0, 0, 100, 100)
    return (min(all_x) - pad, min(all_y) - pad, max(all_x) + pad, max(all_y) + pad)


def _is_door(opening: Any) -> bool:
    return "door" in str(_get(opening, "opening_type", "")).lower()


def _door_midpoint(opening: Any) -> _WorldPt:
    x1 = float(_get(opening, "x1", 0.0))
    y1 = float(_get(opening, "y1", 0.0))
    x2 = float(_get(opening, "x2", 0.0))
    y2 = float(_get(opening, "y2", 0.0))
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


# ---------------------------------------------------------------------------
# Floor plan panel
# ---------------------------------------------------------------------------

ROOM_COLORS = {
    "livingRoom":          "#d4e8d4",
    "bedroom":             "#cfd9e6",
    "kitchen":             "#e8e0cc",
    "bathroom":            "#cce8e8",
    "attachedBathroom":    "#b8d8e8",
    "hallway":             "#ede0d4",
    "diningRoom":          "#ece8d0",
    "garage":              "#dcdcdc",
    "veranda":             "#d4e8cc",
    "verandaOutdoorSpace": "#d4e8cc",
}
DEFAULT_ROOM_COLOR = "#efefef"
HALLWAY_USED_COLOR  = "#ede0d4"
HALLWAY_UNUSED_COLOR = "#f8d4d4"


def _draw_rooms(ax: Any, rooms: List[Any], hallway_usage: Dict[str, Any]) -> None:
    for room in rooms:
        verts = _get(room, "vertices", [])
        if not verts or len(verts) < 3:
            continue
        rtype = str(_get(room, "type", ""))
        rname = str(_get(room, "name", ""))

        # Highlight unused hallways in pale red
        if rtype == "hallway" and rname in hallway_usage and not hallway_usage[rname]["used"]:
            facecolor = HALLWAY_UNUSED_COLOR
        else:
            facecolor = ROOM_COLORS.get(rtype, DEFAULT_ROOM_COLOR)

        patch = MplPolygon(
            verts, closed=True,
            facecolor=facecolor, edgecolor="#555555",
            linewidth=1.2, alpha=0.85, zorder=1,
        )
        ax.add_patch(patch)

        # Room label
        centroid = _room_centroid(room)
        if centroid:
            label = _room_label(room)
            ax.text(
                centroid[0], centroid[1], label,
                ha="center", va="center", fontsize=7.5, weight="bold",
                color="#222222", zorder=5,
                bbox=dict(
                    boxstyle="round,pad=0.25", facecolor="white",
                    edgecolor="#aaaaaa", alpha=0.80, linewidth=0.6,
                ),
            )


def _draw_doors(ax: Any, openings: List[Any]) -> None:
    """Draw door openings as small coloured arcs on the wall."""
    for op in openings:
        if not _is_door(op):
            continue
        x1 = float(_get(op, "x1", 0.0))
        y1 = float(_get(op, "y1", 0.0))
        x2 = float(_get(op, "x2", 0.0))
        y2 = float(_get(op, "y2", 0.0))
        mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0

        otype = str(_get(op, "opening_type", "")).lower()
        color = "#e05d2c" if "main" in otype else ("#2c7fb8" if "back" in otype else "#888888")

        ax.plot([x1, x2], [y1, y2], color=color, linewidth=3.5, solid_capstyle="round", zorder=3)
        ax.plot(mx, my, "o", color=color, markersize=4, zorder=4)


def _draw_paths(ax: Any, paths: List[Any]) -> None:
    """Draw smooth curved paths with directional arrows."""
    for path in paths:
        coords = path.coords
        if not coords or len(coords) < 2:
            continue
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
        color = path.color

        # Draw main path line
        ax.plot(
            xs, ys, color=color, linewidth=2.2,
            alpha=0.85, solid_capstyle="round",
            path_effects=[
                pe.withStroke(linewidth=3.8, foreground="white", alpha=0.5)
            ],
            zorder=6,
        )

        # Draw directional arrow at the midpoint
        mid = len(coords) // 2
        if mid + 1 < len(coords):
            dx = coords[mid + 1][0] - coords[mid][0]
            dy = coords[mid + 1][1] - coords[mid][1]
            ax.annotate(
                "", xy=(coords[mid + 1][0], coords[mid + 1][1]),
                xytext=(coords[mid][0], coords[mid][1]),
                arrowprops=dict(
                    arrowstyle="-|>", color=color,
                    lw=1.5, mutation_scale=10,
                ),
                zorder=7,
            )

        # Start and end dots
        ax.plot(xs[0], ys[0], "o", color=color, markersize=5, zorder=8)
        ax.plot(xs[-1], ys[-1], "s", color=color, markersize=4, zorder=8)


def _draw_overlaps(ax: Any, overlaps: List[Dict[str, Any]]) -> None:
    """Shade overlapping path regions with translucent red."""
    for ov in overlaps:
        geom = ov.get("overlap_geom")
        if geom is None or geom.is_empty:
            continue

        polys = []
        if isinstance(geom, Polygon):
            polys = [geom]
        elif isinstance(geom, MultiPolygon):
            polys = list(geom.geoms)
        else:
            try:
                polys = [g for g in geom.geoms if isinstance(g, Polygon)]
            except Exception:
                pass

        for poly in polys:
            if poly.is_empty:
                continue
            coords = list(poly.exterior.coords)
            patch = MplPolygon(
                coords, closed=True,
                facecolor="#e03030", edgecolor="#cc0000",
                linewidth=0.8, alpha=0.25, zorder=5, hatch="//",
            )
            ax.add_patch(patch)


def _style_floor_ax(ax: Any, rooms: List[Any], title: str) -> None:
    xmin, ymin, xmax, ymax = _get_floor_bounds(rooms)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal", adjustable="box")
    ax.invert_yaxis()
    ax.set_facecolor("#f8f6f0")
    ax.set_title(title, fontsize=12, weight="bold", color="#1a1a1a", pad=10)
    ax.grid(True, color="#ddd8cc", linewidth=0.4, alpha=0.7, zorder=0)
    ax.tick_params(labelsize=7, colors="#555555")
    for spine in ax.spines.values():
        spine.set_edgecolor("#bbbbbb")
        spine.set_linewidth(0.8)


# ---------------------------------------------------------------------------
# Hallway utility bar chart
# ---------------------------------------------------------------------------


def _draw_hallway_chart(ax: Any, hallway_usage: Dict[str, Any]) -> None:
    if not hallway_usage:
        ax.text(0.5, 0.5, "No hallways\nfound", ha="center", va="center",
                transform=ax.transAxes, fontsize=10, color="#888888")
        ax.set_title("Hallway Utility", fontsize=10, weight="bold", color="#1a1a1a")
        return

    names = list(hallway_usage.keys())
    counts = [hallway_usage[n]["count"] for n in names]
    colors = ["#4a90d9" if hallway_usage[n]["used"] else "#e05050" for n in names]

    short_names = [n.replace("hallway", "Hall").replace("Hallway", "Hall") for n in names]

    bars = ax.barh(short_names, counts, color=colors, edgecolor="white",
                   linewidth=0.8, height=0.55)

    for bar, count in zip(bars, counts):
        ax.text(
            bar.get_width() + 0.05, bar.get_y() + bar.get_height() / 2,
            str(count), va="center", ha="left", fontsize=9, weight="bold",
            color="#222222",
        )

    ax.set_xlabel("Paths crossing", fontsize=8, color="#555555")
    ax.set_title("Hallway Utility", fontsize=10, weight="bold", color="#1a1a1a", pad=8)
    ax.set_facecolor("#fafafa")
    ax.grid(axis="x", color="#dddddd", linewidth=0.5, alpha=0.8)
    ax.tick_params(labelsize=8, colors="#444444")
    for spine in ax.spines.values():
        spine.set_edgecolor("#cccccc")

    # Legend patches
    used_patch = mpatches.Patch(color="#4a90d9", label="Used")
    unused_patch = mpatches.Patch(color="#e05050", label="Unused")
    ax.legend(handles=[used_patch, unused_patch], fontsize=7.5,
              loc="lower right", framealpha=0.85)


# ---------------------------------------------------------------------------
# Overlap panel
# ---------------------------------------------------------------------------


def _draw_overlap_panel(ax: Any, overlaps: List[Dict[str, Any]]) -> None:
    ax.axis("off")
    ax.set_title("Path Overlaps", fontsize=10, weight="bold", color="#1a1a1a", pad=8)
    ax.set_facecolor("#fafafa")

    if not overlaps:
        ax.text(0.5, 0.5, "✓  No overlapping\n   path regions",
                ha="center", va="center", transform=ax.transAxes,
                fontsize=10, color="#3a8a3a", weight="bold")
        return

    # Sort by area desc
    sorted_ov = sorted(overlaps, key=lambda o: o["overlap_area"], reverse=True)[:8]

    y = 0.92
    ax.text(0.05, y, f"{len(overlaps)} overlapping pair(s):", fontsize=8.5,
            weight="bold", color="#cc3333", transform=ax.transAxes)
    y -= 0.10

    for ov in sorted_ov:
        label = f"• {ov['path_a']}  ✕  {ov['path_b']}"
        area_txt = f"   area={ov['overlap_area']:.0f} cm²"
        ax.text(0.05, y, label, fontsize=7.5, color="#222222",
                transform=ax.transAxes, clip_on=True)
        y -= 0.09
        ax.text(0.08, y, area_txt, fontsize=7, color="#888888",
                transform=ax.transAxes)
        y -= 0.08
        if y < 0.05:
            break


# ---------------------------------------------------------------------------
# Path legend
# ---------------------------------------------------------------------------


def _draw_legend(ax: Any, paths: List[Any]) -> None:
    ax.axis("off")
    ax.set_facecolor("#f8f6f0")
    ax.set_title("Simulated Paths", fontsize=10, weight="bold", color="#1a1a1a", pad=6)

    seen: Dict[str, str] = {}
    for p in paths:
        seen[p.label] = p.color

    cols = 2
    items = list(seen.items())
    rows = (len(items) + cols - 1) // cols

    for idx, (label, color) in enumerate(items):
        row = idx % rows
        col = idx // rows
        x = 0.04 + col * 0.50
        y = 0.85 - row * 0.14
        ax.plot([x, x + 0.07], [y, y], color=color, linewidth=2.5,
                transform=ax.transAxes, clip_on=False)
        ax.plot(x + 0.035, y, "o", color=color, markersize=4,
                transform=ax.transAxes, clip_on=False)
        ax.text(x + 0.10, y, label, fontsize=7.5, color="#1a1a1a",
                va="center", transform=ax.transAxes, clip_on=False)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def plot_path_simulation(
    rooms: List[Any],
    openings: List[Any],
    paths: List[Any],
    overlaps: List[Dict[str, Any]],
    hallway_usage: Dict[str, Any],
    output_dir: Optional[str] = None,
) -> str:
    """Save a multi-panel path simulation diagnostic plot.

    Layout
    ------
    +-------------------------------------------+----------+
    |                                            |  Hallway |
    |       Floor Plan + Paths + Overlaps        |  Utility |
    |             (main large panel)             |  Chart   |
    |                                            +----------+
    |                                            |  Overlap |
    |                                            |  Summary |
    +-------------------------------------------+----------+
    |        Path Legend        |   Stats info              |
    +-------------------------------------------+----------+
    """
    if output_dir is None:
        here = os.path.dirname(__file__)
        output_dir = os.path.join(here, "output")
    os.makedirs(output_dir, exist_ok=True)
    save_path = _timestamped_path(output_dir)

    dev_print("path", f"Plotting path simulation to: {save_path}")

    # ---- Figure + GridSpec layout -----------------------------------------
    fig = plt.figure(
        figsize=(16, 11),
        dpi=130,
        facecolor="#f5f2ec",
    )
    fig.suptitle(
        "Path Simulation Analysis",
        fontsize=15, weight="bold", color="#111111",
        y=0.98,
    )

    gs = gridspec.GridSpec(
        2, 2,
        figure=fig,
        left=0.04, right=0.97,
        top=0.94, bottom=0.13,
        wspace=0.22, hspace=0.35,
        width_ratios=[2.8, 1],
        height_ratios=[1.4, 1],
    )

    ax_floor = fig.add_subplot(gs[:, 0])           # main — full left column
    ax_hall  = fig.add_subplot(gs[0, 1])            # top-right: hallway chart
    ax_ov    = fig.add_subplot(gs[1, 1])            # bottom-right: overlap list

    # Bottom legend strip (outside gs)
    ax_legend = fig.add_axes([0.04, 0.01, 0.55, 0.10])
    ax_stats  = fig.add_axes([0.62, 0.01, 0.35, 0.10])

    # ---- Main floor plan ---------------------------------------------------
    _draw_rooms(ax_floor, rooms, hallway_usage)
    _draw_doors(ax_floor, openings)
    _draw_overlaps(ax_floor, overlaps)
    _draw_paths(ax_floor, paths)
    _style_floor_ax(
        ax_floor, rooms,
        f"Floor Plan  ·  {len(paths)} paths simulated  ·  "
        f"{len(overlaps)} overlap(s)",
    )

    # ---- Hallway chart -----------------------------------------------------
    _draw_hallway_chart(ax_hall, hallway_usage)

    # ---- Overlap summary ---------------------------------------------------
    _draw_overlap_panel(ax_ov, overlaps)

    # ---- Legend strip ------------------------------------------------------
    _draw_legend(ax_legend, paths)

    # ---- Stats strip -------------------------------------------------------
    ax_stats.axis("off")
    ax_stats.set_facecolor("#f8f6f0")
    unused = sum(1 for v in hallway_usage.values() if not v["used"])
    used   = sum(1 for v in hallway_usage.values() if v["used"])
    stats_lines = [
        f"Paths simulated : {len(paths)}",
        f"Overlapping pairs : {len(overlaps)}",
        f"Hallways used / total : {used} / {len(hallway_usage)}",
        f"Unused hallways : {unused}  {'⚠' if unused else '✓'}",
    ]
    for i, line in enumerate(stats_lines):
        ax_stats.text(
            0.05, 0.80 - i * 0.22, line,
            fontsize=8, color="#333333",
            transform=ax_stats.transAxes, va="top",
        )
    ax_stats.set_title("Summary", fontsize=9, weight="bold",
                        color="#1a1a1a", pad=4)

    # ---- Colour bar legend for room types (inline) -------------------------
    legend_patches = [
        mpatches.Patch(facecolor="#ffcccc", edgecolor="#cc0000",
                       hatch="//", alpha=0.5, label="Path overlap zone"),
        mpatches.Patch(facecolor=HALLWAY_UNUSED_COLOR, edgecolor="#cc5555",
                       label="Unused hallway"),
    ]
    ax_floor.legend(
        handles=legend_patches, loc="lower right",
        fontsize=7.5, framealpha=0.90, title="Indicators",
        title_fontsize=8,
    )

    plt.savefig(
        save_path, dpi=130, bbox_inches="tight",
        facecolor=fig.get_facecolor(),
    )
    plt.close(fig)

    dev_print("path", "Plot saved successfully.")
    return save_path


# ---------------------------------------------------------------------------
# Legacy function kept for backwards compatibility
# ---------------------------------------------------------------------------


def plot_nav_mesh(
    nav_mesh: Any,
    total_floor: Any,
    rooms: List[Any],
    output_dir: Optional[str] = None,
) -> str:
    """Legacy nav mesh plotter — now a thin wrapper that saves a simple room outline."""
    if output_dir is None:
        here = os.path.dirname(__file__)
        output_dir = os.path.join(here, "output")
    os.makedirs(output_dir, exist_ok=True)
    save_path = _timestamped_path(output_dir).replace("_paths", "_navmesh")

    fig, ax = plt.subplots(figsize=(10, 8), dpi=110, facecolor="#f5f2ec")
    ax.set_facecolor("#f8f6f0")
    ax.set_title("Navigation Mesh (room outlines)", fontsize=11, weight="bold")

    for room in rooms:
        verts = _get(room, "vertices", [])
        if not verts or len(verts) < 3:
            continue
        rtype = str(_get(room, "type", ""))
        color = ROOM_COLORS.get(rtype, DEFAULT_ROOM_COLOR)
        patch = MplPolygon(verts, closed=True, facecolor=color,
                           edgecolor="#555555", linewidth=1.2, alpha=0.8)
        ax.add_patch(patch)
        c = _room_centroid(room)
        if c:
            ax.text(c[0], c[1], _room_label(room), ha="center", va="center",
                    fontsize=7, weight="bold", color="#222222")

    xmin, ymin, xmax, ymax = _get_floor_bounds(rooms)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal")
    ax.invert_yaxis()
    ax.grid(True, color="#dddddd", linewidth=0.4, alpha=0.6)

    plt.tight_layout()
    plt.savefig(save_path, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return save_path


# expose constant for import
HALLWAY_UNUSED_COLOR = "#f8d4d4"

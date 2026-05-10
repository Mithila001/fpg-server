"""Plotter for navigation mesh visualization during path simulation setup.

Generates a clear plot of the calculated nav mesh with:
- Navigation mesh (walkable area) - highlighted with blue overlay
- Floor plan rooms with type-based colors and clear labels
- Walls/obstacles shown as distinct red hatched areas
- Legend explaining the visualization
- Timestamp-based file saving to dev/output directory

No imports from outside this package.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
from shapely.geometry import MultiPolygon, Polygon

from .. import path_sim_config
from ..util._dev_print import dev_print


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Safe attribute/key access."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _to_shapely_coords(geom: Any) -> Any:
    """Extract coordinates from Shapely geometry."""
    if geom is None or getattr(geom, "is_empty", True):
        return None
    if isinstance(geom, Polygon):
        return list(geom.exterior.coords)
    return None


def _get_room_centroid(room: Any) -> Tuple[float, float] | None:
    """Calculate room centroid for label placement."""
    verts = _get(room, "vertices", [])
    if not verts or len(verts) < 3:
        return None
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def _get_room_label(room: Any) -> str:
    """Get a short label for the room."""
    room_type = str(_get(room, "type", "unknown"))
    # Convert camelCase to readable format
    label = room_type.replace("attachedBathroom", "A.Bath")
    label = label.replace("verandaOutdoorSpace", "Veranda")
    label = label.replace("diningRoom", "Dining")
    label = label.replace("bedroom", "Bed")
    label = label.replace("kitchen", "Kit")
    label = label.replace("bathroom", "Bath")
    label = label.replace("hallway", "Hall")
    label = label.replace("livingRoom", "Living")
    label = label.replace("garage", "Garage")
    return label if label else "?"


def _timestamped_png_path(output_dir: str) -> str:
    """Generate timestamped PNG filename."""
    os.makedirs(output_dir, exist_ok=True)
    now = datetime.now()
    ms = now.microsecond // 1000
    fname = now.strftime(f"%Y-%m-%d-%H-%M-%S-{ms:03d}") + ".png"
    return os.path.join(output_dir, fname)


def _draw_nav_mesh(ax: Any, nav_mesh: Any, total_floor: Any) -> None:
    """Draw navigation mesh with clear walkable vs non-walkable distinction.

    Shows walkable area with blue overlay and walls with red hatching.
    """
    if nav_mesh is None or getattr(nav_mesh, "is_empty", True):
        return

    # First, draw NON-walkable areas (walls/obstacles) in red with hatching
    if total_floor is not None and not getattr(total_floor, "is_empty", True):
        # Non-walkable = total_floor - nav_mesh
        non_walkable = total_floor.difference(nav_mesh)

        polys = []
        if isinstance(non_walkable, MultiPolygon):
            polys = list(non_walkable.geoms)
        elif isinstance(non_walkable, Polygon):
            polys = [non_walkable]

        for poly in polys:
            if isinstance(poly, Polygon) and not poly.is_empty:
                coords = list(poly.exterior.coords)
                patch = MplPolygon(
                    coords,
                    closed=True,
                    facecolor="#ffcccc",  # Light red background for walls
                    edgecolor="#cc0000",
                    linewidth=1.5,
                    alpha=0.6,
                    hatch="//",  # Red hatching pattern for walls
                )
                ax.add_patch(patch)

    # Now draw walkable area (nav mesh) with blue overlay
    polys = []
    if isinstance(nav_mesh, MultiPolygon):
        polys = list(nav_mesh.geoms)
    elif isinstance(nav_mesh, Polygon):
        polys = [nav_mesh]

    for poly in polys:
        if isinstance(poly, Polygon) and not poly.is_empty:
            coords = list(poly.exterior.coords)
            patch = MplPolygon(
                coords,
                closed=True,
                facecolor="#b3d9ff",  # Bright blue for walkable area
                edgecolor="#0066cc",
                linewidth=2.0,
                alpha=0.3,
            )
            ax.add_patch(patch)

            # Draw holes (internal obstacles) if any
            for hole in poly.interiors:
                hole_coords = list(hole.coords)
                hole_patch = MplPolygon(
                    hole_coords,
                    closed=True,
                    facecolor="#ffcccc",
                    edgecolor="#cc0000",
                    linewidth=1.2,
                    alpha=0.7,
                    hatch="///",
                )
                ax.add_patch(hole_patch)


def _draw_rooms(ax: Any, rooms: List[Any]) -> None:
    """Draw filled room polygons with labels."""
    room_colors = path_sim_config.PLOT_ROOM_COLORS
    default_color = path_sim_config.PLOT_DEFAULT_ROOM_COLOR

    for room in rooms:
        verts = _get(room, "vertices", [])
        if not verts or len(verts) < 3:
            continue

        rtype = str(_get(room, "type", ""))
        color = room_colors.get(rtype, default_color)

        patch = MplPolygon(
            verts,
            closed=True,
            facecolor=color,
            edgecolor="#4a4a4a",
            linewidth=0.8,
            alpha=0.7,
        )
        ax.add_patch(patch)

        # Add room label at centroid
        centroid = _get_room_centroid(room)
        if centroid:
            label = _get_room_label(room)
            ax.text(
                centroid[0],
                centroid[1],
                label,
                ha="center",
                va="center",
                fontsize=8,
                weight="bold",
                color="#1f1f1f",
                bbox=dict(
                    boxstyle="round,pad=0.3",
                    facecolor="white",
                    edgecolor="#888888",
                    alpha=0.85,
                    linewidth=0.5,
                ),
            )


def _set_ax_style(ax: Any, title: str, rooms: List[Any]) -> None:
    """Set axis styling and bounds."""
    bg_color = path_sim_config.PLOT_PANEL_BG_COLOR
    text_color = path_sim_config.PLOT_TEXT_COLOR
    grid_color = path_sim_config.PLOT_GRID_COLOR

    ax.set_facecolor(bg_color)
    ax.set_title(title, color=text_color, fontsize=11, pad=8, weight="bold")
    ax.tick_params(colors=text_color, labelsize=6)
    ax.grid(True, color=grid_color, linewidth=0.4, alpha=0.5)

    for spine in ax.spines.values():
        spine.set_edgecolor("#b9b3a8")
        spine.set_linewidth(0.6)

    # Set bounds based on room coordinates
    all_x: List[float] = []
    all_y: List[float] = []
    for room in rooms:
        for v in _get(room, "vertices", []):
            all_x.append(v[0])
            all_y.append(v[1])

    if all_x:
        pad = 50.0
        ax.set_xlim(min(all_x) - pad, max(all_x) + pad)
        ax.set_ylim(min(all_y) - pad, max(all_y) + pad)

    ax.set_aspect("equal", adjustable="box")
    ax.invert_yaxis()  # Standard floor plan orientation


def plot_nav_mesh(
    nav_mesh: Any,
    total_floor: Any,
    rooms: List[Any],
    output_dir: str | None = None,
) -> str:
    """Plot nav mesh with room labels and save to timestamped file.

    Parameters
    ----------
    nav_mesh : Shapely Polygon/MultiPolygon
        The walkable area (nav mesh minus walls)
    total_floor : Shapely Polygon/MultiPolygon
        Raw union of all room polygons
    rooms : List[dict or object]
        List of room objects with 'type' and 'vertices'
    output_dir : str, optional
        Output directory. If None, uses dev/output relative to this file.

    Returns
    -------
    str
        Absolute path to saved PNG file
    """
    if output_dir is None:
        here = os.path.dirname(__file__)
        output_dir = os.path.join(here, "output")

    os.makedirs(output_dir, exist_ok=True)
    save_path = _timestamped_png_path(output_dir)

    dev_print("path", f"Plotting nav mesh to: {save_path}")

    # Create figure
    fig, ax = plt.subplots(
        figsize=(12, 10),
        dpi=120,
        facecolor=path_sim_config.PLOT_BG_COLOR,
    )

    # Draw layers bottom-to-top:
    # 1. Nav mesh (walkable vs non-walkable distinction)
    # 2. Rooms with labels
    _draw_nav_mesh(ax, nav_mesh, total_floor)
    _draw_rooms(ax, rooms)

    _set_ax_style(
        ax,
        f"Navigation Mesh Visualization ({len(rooms)} rooms)",
        rooms,
    )

    # Enforce vertical flip so top of floorplan appears at bottom of image
    try:
        ax.invert_yaxis()
    except Exception:
        pass

    # Create legend
    legend_elements = [
        MplPolygon(
            [[0, 0]],
            closed=True,
            facecolor="#b3d9ff",
            edgecolor="#0066cc",
            linewidth=2,
            alpha=0.3,
            label="Walkable Area (Nav Mesh)",
        ),
        MplPolygon(
            [[0, 0]],
            closed=True,
            facecolor="#ffcccc",
            edgecolor="#cc0000",
            linewidth=1.5,
            alpha=0.6,
            hatch="//",
            label="Walls & Obstacles",
        ),
    ]
    ax.legend(
        handles=legend_elements,
        loc="upper left",
        fontsize=9,
        title="Legend",
        title_fontsize=10,
        framealpha=0.95,
    )

    # Add info text
    nav_area = nav_mesh.area if hasattr(nav_mesh, "area") else 0.0
    floor_area = total_floor.area if hasattr(total_floor, "area") else 0.0
    info_text = (
        f"Walkable Area: {nav_area:.1f} cm² | "
        f"Total Floor: {floor_area:.1f} cm² | "
        f"Grid Resolution: {path_sim_config.GRID_RESOLUTION_CM}cm"
    )
    ax.text(
        0.5,
        -0.08,
        info_text,
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=8,
        color=path_sim_config.PLOT_TEXT_COLOR,
        style="italic",
    )

    plt.tight_layout()
    plt.savefig(
        save_path, dpi=120, bbox_inches="tight", facecolor=path_sim_config.PLOT_BG_COLOR
    )
    plt.close(fig)

    dev_print("path", "Nav mesh plot saved successfully.")
    return save_path

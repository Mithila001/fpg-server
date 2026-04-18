from __future__ import annotations

import math
import os
from typing import Any, Dict, Sequence, Tuple

from shapely.geometry import box, LineString
from shapely.ops import unary_union

from ..utils import (
    extract_contact_points,
    is_close_to_any,
    iter_polygons,
    iter_segments,
    segment_orientation,
)


def _plot_inward_pocket_debug(
    rooms: Sequence[Dict[str, Any]],
    hull: Any,
    pockets: Any,
    tracked_segments: Sequence[LineString],
    bad_segments: Sequence[LineString],
    output_dir: str | None = None,
) -> None:
    if output_dir is None:
        output_dir = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "..",
                "..",
                "..",
                "test",
                "outputs",
                "score_inward_pockats",
            )
        )

    os.makedirs(output_dir, exist_ok=True)

    try:
        import matplotlib.pyplot as plt
        from matplotlib.patches import Polygon as MplPolygon
    except ImportError as exc:
        print(
            f"Unable to save inward pocket debug plot because matplotlib is not installed: {exc}"
        )
        print(f"Intended output directory: {output_dir}")
        return

    def _draw_rooms(ax: Any) -> None:
        for room in rooms:
            x = float(room["x"])
            y = float(room["y"])
            w = float(room["x_end"]) - x
            h = float(room["y_end"]) - y
            rect = plt.Rectangle((x, y), w, h, facecolor="lightblue", edgecolor="black", alpha=0.3)
            ax.add_patch(rect)

    def _draw_polygon(ax: Any, polygon: Any, **kwargs: Any) -> None:
        if polygon.is_empty:
            return
        if polygon.geom_type == "Polygon":
            patch = MplPolygon(list(polygon.exterior.coords), closed=True, **kwargs)
            ax.add_patch(patch)
        else:
            for poly in getattr(polygon, "geoms", []):
                patch = MplPolygon(list(poly.exterior.coords), closed=True, **kwargs)
                ax.add_patch(patch)

    def _draw_segments(ax: Any, segments: Sequence[LineString], **kwargs: Any) -> None:
        for segment in segments:
            xs, ys = segment.xy
            ax.plot(xs, ys, **kwargs)

    all_x = [float(room["x"]) for room in rooms] + [float(room["x_end"]) for room in rooms]
    all_y = [float(room["y"]) for room in rooms] + [float(room["y_end"]) for room in rooms]
    padding = max(1.0, max(all_x) - min(all_x), max(all_y) - min(all_y))
    x_min = min(all_x) - padding * 0.05
    x_max = max(all_x) + padding * 0.05
    y_min = min(all_y) - padding * 0.05
    y_max = max(all_y) + padding * 0.05

    x_min = math.floor(x_min / 10.0) * 10.0
    x_max = math.ceil(x_max / 10.0) * 10.0
    y_min = math.floor(y_min / 10.0) * 10.0
    y_max = math.ceil(y_max / 10.0) * 10.0

    x_ticks = [x_min + i * 10.0 for i in range(int((x_max - x_min) / 10.0) + 1)]
    y_ticks = [y_min + i * 10.0 for i in range(int((y_max - y_min) / 10.0) + 1)]

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    titles = [
        "Union + detected pockets",
        "Tracked pocket boundary segments",
        "Violating inward pocket segments",
    ]

    for ax, title in zip(axes, titles):
        _draw_rooms(ax)
        if hull is not None and hasattr(hull, "exterior"):
            xs, ys = hull.exterior.xy
            ax.plot(xs, ys, color="gray", linestyle="--", linewidth=1)
        ax.set_title(title)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)
        ax.set_xticks(x_ticks)
        ax.set_yticks(y_ticks)
        ax.grid(True, which="major", color="lightgray", linestyle="--", linewidth=0.5)

    _draw_polygon(axes[0], pockets, facecolor="red", edgecolor="darkred", alpha=0.35)
    _draw_segments(axes[1], tracked_segments, color="orange", linewidth=2)
    _draw_segments(axes[2], bad_segments, color="red", linewidth=3)

    axes[0].legend([plt.Line2D([0], [0], color="lightblue", lw=10, alpha=0.3), plt.Line2D([0], [0], color="red", lw=10, alpha=0.35)], ["rooms", "pockets"], frameon=False)

    import uuid
    from datetime import datetime

    output_path = os.path.join(
        output_dir,
        f"inward_pocket_debug_{datetime.utcnow():%Y%m%d_%H%M%S_%f}_{uuid.uuid4().hex}.png",
    )
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"Saved inward pocket debug plot to: {output_path}")


def detect_inward_pocket_violation(
    rooms: Sequence[Dict[str, Any]],
    max_inward_length: float = 20.0,
    tolerance: float = 1e-6,
) -> Tuple[bool, Dict[str, Any]]:
    """Detect inward pocket segments and flag segments longer than threshold."""
    diagnostics: Dict[str, Any] = {
        "pocket_count": 0,
        "max_inward_segment_length": 0.0,
        "violating_segments": [],
        "threshold": float(max_inward_length),
        "tolerance": float(tolerance),
        "geometry_status": "ok",
    }
    
    
    detect_inward_pocket_violation_v2(rooms,max_inward_length, tolerance)

    if not rooms:
        diagnostics["geometry_status"] = "no_rooms"
        return False, diagnostics

    union_geom = unary_union(
        [
            box(
                float(room["x"]),
                float(room["y"]),
                float(room["x_end"]),
                float(room["y_end"]),
            )
            for room in rooms
        ]
    )

    if union_geom.is_empty:
        diagnostics["geometry_status"] = "empty_union"
        return False, diagnostics

    hull = union_geom.convex_hull
    pockets = hull.difference(union_geom)
    if pockets.is_empty:
        diagnostics["geometry_status"] = "no_pockets"
        return False, diagnostics

    plan_boundary = union_geom.boundary
    hull_boundary = hull.boundary

    violating_segments: list[Dict[str, Any]] = []
    tracked_segments: list[LineString] = []
    bad_segments: list[LineString] = []

    for pocket_index, pocket in enumerate(iter_polygons(pockets)):
        diagnostics["pocket_count"] += 1
        ring = pocket.exterior
        hull_contacts = extract_contact_points(ring.intersection(hull_boundary))

        hull_segment_orientations: set[str] = set()
        for segment in iter_segments(ring):
            if segment.length <= float(tolerance):
                continue
            if segment.intersection(hull_boundary).length > float(tolerance):
                hull_segment_orientations.add(segment_orientation(segment, tolerance))

        for segment in iter_segments(ring):
            seg_length = float(segment.length)
            if seg_length <= float(tolerance):
                continue

            on_plan = segment.intersection(plan_boundary).length > float(tolerance)
            on_hull = segment.intersection(hull_boundary).length > float(tolerance)
            if not on_plan or on_hull:
                continue

            coords = list(segment.coords)
            start = (float(coords[0][0]), float(coords[0][1]))
            end = (float(coords[1][0]), float(coords[1][1]))

            start_on_hull_contact = is_close_to_any(start, hull_contacts, float(tolerance) * 10.0)
            end_on_hull_contact = is_close_to_any(end, hull_contacts, float(tolerance) * 10.0)

            # Inward walls generally connect hull-contact point to deeper pocket boundary point.
            inward_by_endpoints = (start_on_hull_contact and not end_on_hull_contact) or (
                end_on_hull_contact and not start_on_hull_contact
            )

            if not inward_by_endpoints:
                continue

            current_orientation = segment_orientation(segment, tolerance)
            if hull_segment_orientations and current_orientation in hull_segment_orientations:
                continue

            tracked_segments.append(segment)
            diagnostics["max_inward_segment_length"] = max(
                float(diagnostics["max_inward_segment_length"]),
                seg_length,
            )

            if seg_length > float(max_inward_length):
                bad_segments.append(segment)
                violating_segments.append(
                    {
                        "pocket_index": int(pocket_index),
                        "length": seg_length,
                        "orientation": current_orientation,
                        "x1": start[0],
                        "y1": start[1],
                        "x2": end[0],
                        "y2": end[1],
                    }
                )

    print("\n------------------ Inward Pockets\n")
    _plot_inward_pocket_debug(
        rooms=rooms,
        hull=hull,
        pockets=pockets,
        tracked_segments=tracked_segments,
        bad_segments=bad_segments,
        output_dir=None,
    )

    diagnostics["violating_segments"] = violating_segments
    return len(violating_segments) > 0, diagnostics



def detect_inward_pocket_violation_v2(
    rooms: Sequence[Dict[str, Any]],
    max_inward_length: float = 20.0,
    tolerance: float = 1e-6,
) -> Tuple[bool, Dict[str, Any]]:
    """Second Version of the detect_inward_pocket_violation() function, still under development.

    This version currently plots the floor plan and convex hull as the first debug step.
    """
    diagnostics: Dict[str, Any] = {
        "pocket_count": 0,
        "max_inward_segment_length": 0.0,
        "violating_segments": [],
        "threshold": float(max_inward_length),
        "tolerance": float(tolerance),
        "geometry_status": "ok",
    }

    if not rooms:
        diagnostics["geometry_status"] = "no_rooms"
        return False, diagnostics

    union_geom = unary_union(
        [
            box(
                float(room["x"]),
                float(room["y"]),
                float(room["x_end"]),
                float(room["y_end"]),
            )
            for room in rooms
        ]
    )

    if union_geom.is_empty:
        diagnostics["geometry_status"] = "empty_union"
        return False, diagnostics

    hull = union_geom.convex_hull
    pockets = hull.difference(union_geom)
    if pockets.is_empty:
        diagnostics["geometry_status"] = "no_pockets"

    pockets_info = _compute_red_pocket_angle_info(
        union_geom=union_geom,
        hull=hull,
        pockets=pockets,
        tolerance=tolerance,
    )
    hull_contact_points = _extract_pocket_hull_contact_points(hull=hull, pockets=pockets)

    # _debug_steps_plotter(
    #     rooms=rooms,
    #     union_geom=union_geom,
    #     hull=hull,
    #     pockets=pockets,
    #     pockets_info=pockets_info,
    #     hull_contact_points=hull_contact_points,
    # )

    purple_groups: list[Dict[str, Any]] = []
    violating_segments: list[Dict[str, Any]] = []
    overall_max_delta = 0.0

    for pocket_index, pocket_info in enumerate(pockets_info):
        if not pocket_info["is_red_pocket"]:
            continue

        group_entries: list[Dict[str, Any]] = []
        max_delta = 0.0
        max_segment: LineString | None = None

        orientation = pocket_info["opposing_orientation"]
        if orientation is None:
            purple_groups.append(
                {
                    "pocket_index": pocket_index,
                    "convex_orientation": pocket_info["convex_orientation"],
                    "opposing_orientation": None,
                    "max_delta": 0.0,
                    "segments": [],
                    "violates": False,
                }
            )
            continue

        for segment in pocket_info["opposing_segments"]:
            coords = list(segment.coords)
            x1, y1 = float(coords[0][0]), float(coords[0][1])
            x2, y2 = float(coords[1][0]), float(coords[1][1])
            if orientation == "vertical":
                delta = abs(y2 - y1)
            else:
                delta = abs(x2 - x1)
            group_entries.append(
                {
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "orientation": orientation,
                    "delta": delta,
                }
            )
            if delta > max_delta:
                max_delta = delta
                max_segment = segment

        purple_groups.append(
            {
                "pocket_index": pocket_index,
                "convex_orientation": pocket_info["convex_orientation"],
                "opposing_orientation": pocket_info["opposing_orientation"],
                "max_delta": max_delta,
                "segments": group_entries,
                "violates": max_delta > float(max_inward_length),
            }
        )

        overall_max_delta = max(overall_max_delta, max_delta)
        if max_segment is not None and max_delta > float(max_inward_length):
            coords = list(max_segment.coords)
            violating_segments.append(
                {
                    "pocket_index": pocket_index,
                    "length": max_delta,
                    "orientation": pocket_info["opposing_orientation"],
                    "x1": float(coords[0][0]),
                    "y1": float(coords[0][1]),
                    "x2": float(coords[1][0]),
                    "y2": float(coords[1][1]),
                }
            )

    diagnostics["purple_segment_groups"] = purple_groups
    diagnostics["violating_segments"] = violating_segments
    diagnostics["max_inward_segment_length"] = overall_max_delta
    diagnostics["pocket_count"] = sum(1 for _ in iter_polygons(pockets))

    print(
        f"DEBUG inward pocket v2: {len(violating_segments)} violations, max_delta={overall_max_delta:.2f}, threshold={max_inward_length}"
    )

    return len(violating_segments) > 0, diagnostics


def _iter_geometry_segments(geometry: Any) -> list[LineString]:
    segments: list[LineString] = []
    if geometry.is_empty:
        return segments
    if geometry.geom_type == "LineString":
        segments.append(LineString(geometry.coords))
        return segments
    if geometry.geom_type == "MultiLineString":
        for line in geometry.geoms:
            segments.append(LineString(line.coords))
        return segments
    if geometry.geom_type == "GeometryCollection":
        for item in geometry.geoms:
            segments.extend(_iter_geometry_segments(item))
        return segments
    return segments


def _get_convex_orientation(hull_segments: Sequence[LineString], tolerance: float = 1e-6) -> str | None:
    if not hull_segments:
        return None
    orientation_lengths = {"horizontal": 0.0, "vertical": 0.0}
    for segment in hull_segments:
        orient = segment_orientation(segment, tolerance)
        if orient in orientation_lengths:
            orientation_lengths[orient] += float(segment.length)
    if orientation_lengths["horizontal"] >= orientation_lengths["vertical"]:
        return "horizontal"
    return "vertical"


def _compute_red_pocket_angle_info(
    union_geom: Any,
    hull: Any,
    pockets: Any,
    tolerance: float = 1e-6,
) -> list[Dict[str, Any]]:
    plan_boundary = union_geom.boundary
    pocket_infos: list[Dict[str, Any]] = []
    for pocket in iter_polygons(pockets):
        outer_segments: list[LineString] = []
        hull_segments: list[LineString] = []
        for segment in iter_segments(pocket.exterior):
            if segment.length <= float(tolerance):
                continue
            if segment.intersection(plan_boundary).length > float(tolerance):
                outer_segments.append(segment)
        hull_contact_geom = pocket.exterior.intersection(hull.boundary)
        hull_segments.extend(_iter_geometry_segments(hull_contact_geom))
        convex_orientation = _get_convex_orientation(hull_segments, tolerance)
        opposing_orientation = None
        if convex_orientation == "horizontal":
            opposing_orientation = "vertical"
        elif convex_orientation == "vertical":
            opposing_orientation = "horizontal"

        opposing_segments: list[LineString] = []
        if opposing_orientation is not None:
            for segment in outer_segments:
                if segment_orientation(segment, tolerance) == opposing_orientation:
                    opposing_segments.append(segment)

        pocket_infos.append(
            {
                "pocket": pocket,
                "outer_segments": outer_segments,
                "hull_segments": hull_segments,
                "convex_orientation": convex_orientation,
                "opposing_orientation": opposing_orientation,
                "opposing_segments": opposing_segments,
                "is_red_pocket": bool(hull_segments) and len(outer_segments) != 2,
            }
        )
    return pocket_infos


def _extract_pocket_hull_contact_points(hull: Any, pockets: Any, tolerance: float = 1e-6) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for pocket in iter_polygons(pockets):
        contact_geom = pocket.exterior.intersection(hull.boundary)
        for point in extract_contact_points(contact_geom):
            if point not in points:
                points.append(point)
    return points


def _debug_steps_plotter(
    rooms: Sequence[Dict[str, Any]],
    union_geom: Any,
    hull: Any,
    pockets: Any,
    pockets_info: Sequence[Dict[str, Any]],
    hull_contact_points: Sequence[tuple[float, float]],
    output_dir: str | None = None,
) -> None:
    """Save a debug plot of the floor plan, convex hull, and detected pockets."""
    if output_dir is None:
        output_dir = os.path.abspath(os.path.dirname(__file__))

    os.makedirs(output_dir, exist_ok=True)

    try:
        import matplotlib.pyplot as plt
        from matplotlib.patches import Polygon as MplPolygon
    except ImportError as exc:
        print(
            f"Unable to save inward pocket debug plot because matplotlib is not installed: {exc}"
        )
        print(f"Intended output directory: {output_dir}")
        return

    def _draw_rooms(ax: Any) -> None:
        for room in rooms:
            x = float(room["x"])
            y = float(room["y"])
            w = float(room["x_end"]) - x
            h = float(room["y_end"]) - y
            rect = plt.Rectangle((x, y), w, h, facecolor="lightblue", edgecolor="black", alpha=0.4)
            ax.add_patch(rect)

    def _draw_polygon(ax: Any, polygon: Any, **kwargs: Any) -> None:
        if polygon.is_empty:
            return
        if polygon.geom_type == "Polygon":
            patch = MplPolygon(list(polygon.exterior.coords), closed=True, **kwargs)
            ax.add_patch(patch)
        else:
            for poly in getattr(polygon, "geoms", []):
                patch = MplPolygon(list(poly.exterior.coords), closed=True, **kwargs)
                ax.add_patch(patch)

    def _draw_boundary(ax: Any, geometry: Any, **kwargs: Any) -> None:
        if geometry.is_empty:
            return
        boundary = geometry.boundary
        if boundary.is_empty:
            return
        if hasattr(boundary, "geoms"):
            for segment in boundary.geoms:
                xs, ys = segment.xy
                ax.plot(xs, ys, **kwargs)
        else:
            xs, ys = boundary.xy
            ax.plot(xs, ys, **kwargs)

    def _draw_segments(ax: Any, segments: Sequence[LineString], **kwargs: Any) -> None:
        for segment in segments:
            xs, ys = segment.xy
            ax.plot(xs, ys, **kwargs)

    pockets_info = pockets_info
    hull_contact_points = hull_contact_points

    all_x = [float(room["x"]) for room in rooms] + [float(room["x_end"]) for room in rooms]
    all_y = [float(room["y"]) for room in rooms] + [float(room["y_end"]) for room in rooms]
    padding = max(1.0, max(all_x) - min(all_x), max(all_y) - min(all_y))
    x_min = min(all_x) - padding * 0.05
    x_max = max(all_x) + padding * 0.05
    y_min = min(all_y) - padding * 0.05
    y_max = max(all_y) + padding * 0.05

    x_min = math.floor(x_min / 10.0) * 10.0
    x_max = math.ceil(x_max / 10.0) * 10.0
    y_min = math.floor(y_min / 10.0) * 10.0
    y_max = math.ceil(y_max / 10.0) * 10.0

    fig, axes = plt.subplots(1, 3, figsize=(30, 10))
    titles = [
        "Floor Plan with Convex Hull",
        "Pocket-Facing Outer Wall Segments",
        "Red Pocket Angle Highlights",
    ]

    for ax, title in zip(axes, titles):
        ax.set_title(title)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)
        ax.grid(True, which="major", color="lightgray", linestyle="--", linewidth=0.5)

    # Left plot: rooms, hull, pockets
    _draw_rooms(axes[0])
    _draw_boundary(axes[0], hull, color="black", linewidth=2, linestyle="--")
    _draw_polygon(axes[0], pockets, facecolor="red", edgecolor="darkred", alpha=0.25)
    axes[0].legend(
        [
            plt.Line2D([0], [0], color="lightblue", lw=10, alpha=0.4),
            plt.Line2D([0], [0], color="black", lw=2, linestyle="--"),
            plt.Line2D([0], [0], color="red", lw=10, alpha=0.25),
        ],
        ["rooms", "convex hull", "pockets"],
        frameon=False,
    )

    # Middle plot: rooms, pocket-facing outer walls, hull contacts, and context boundaries
    _draw_rooms(axes[1])
    _draw_boundary(axes[1], union_geom, color="gray", linewidth=1, linestyle="-")
    _draw_boundary(axes[1], hull, color="black", linewidth=2, linestyle="--")

    for pocket_info in pockets_info:
        wall_color = "yellow" if len(pocket_info["outer_segments"]) == 2 else "red"
        _draw_segments(axes[1], pocket_info["outer_segments"], color=wall_color, linewidth=4)
        _draw_segments(axes[1], pocket_info["hull_segments"], color="green", linewidth=3)

    if hull_contact_points:
        xs, ys = zip(*hull_contact_points)
        axes[1].scatter(xs, ys, color="magenta", edgecolor="black", linewidth=1.5, s=120, zorder=6)

    axes[1].legend(
        [
            plt.Line2D([0], [0], color="lightblue", lw=10, alpha=0.4),
            plt.Line2D([0], [0], color="black", lw=2, linestyle="--"),
            plt.Line2D([0], [0], color="yellow", lw=4),
            plt.Line2D([0], [0], color="red", lw=4),
            plt.Line2D([0], [0], color="green", lw=3),
            plt.Line2D([0], [0], marker="o", color="magenta", linestyle="", markersize=10, markeredgecolor="black"),
        ],
        ["rooms", "convex hull", "2-wall pockets", "other pocket walls", "pocket convex lines", "hull contact points"],
        frameon=False,
    )

    # Right plot: red pocket angle highlights
    _draw_rooms(axes[2])
    _draw_polygon(axes[2], pockets, facecolor="red", edgecolor="darkred", alpha=0.25)
    for pocket_info in pockets_info:
        if not pocket_info["is_red_pocket"]:
            continue
        _draw_segments(axes[2], pocket_info["hull_segments"], color="green", linewidth=3)
        _draw_segments(axes[2], pocket_info["opposing_segments"], color="purple", linewidth=4)

    axes[2].legend(
        [
            plt.Line2D([0], [0], color="lightblue", lw=10, alpha=0.4),
            plt.Line2D([0], [0], color="red", lw=10, alpha=0.25),
            plt.Line2D([0], [0], color="green", lw=3),
            plt.Line2D([0], [0], color="purple", lw=4),
        ],
        ["rooms", "pockets", "pocket convex lines", "opposing walls"],
        frameon=False,
    )

    import uuid
    from datetime import datetime

    output_path = os.path.join(
        output_dir,
        f"debug_inward_pocket_step_{datetime.utcnow():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}.png",
    )
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"Saved debug plot to: {output_path}")

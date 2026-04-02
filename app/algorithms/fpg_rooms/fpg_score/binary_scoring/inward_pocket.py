from __future__ import annotations

from typing import Any, Dict, Sequence, Tuple

from shapely.geometry import box
from shapely.ops import unary_union

from ..utils import (
    extract_contact_points,
    is_close_to_any,
    iter_polygons,
    iter_segments,
    segment_orientation,
)


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

            diagnostics["max_inward_segment_length"] = max(
                float(diagnostics["max_inward_segment_length"]),
                seg_length,
            )

            if seg_length > float(max_inward_length):
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

    diagnostics["violating_segments"] = violating_segments
    return len(violating_segments) > 0, diagnostics

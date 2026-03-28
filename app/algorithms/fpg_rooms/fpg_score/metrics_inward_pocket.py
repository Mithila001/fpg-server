from __future__ import annotations

from typing import Any, Dict, Iterable, Sequence, Tuple

from shapely.geometry import GeometryCollection, LineString, MultiPolygon, Point, Polygon, box
from shapely.ops import unary_union


def _iter_polygons(geometry: Any) -> Iterable[Polygon]:
    if geometry.is_empty:
        return
    if isinstance(geometry, Polygon):
        yield geometry
        return
    if isinstance(geometry, MultiPolygon):
        for poly in geometry.geoms:
            yield poly
        return
    if isinstance(geometry, GeometryCollection):
        for item in geometry.geoms:
            if isinstance(item, Polygon):
                yield item
            elif isinstance(item, MultiPolygon):
                for poly in item.geoms:
                    yield poly


def _iter_segments(ring: Any) -> Iterable[LineString]:
    coords = list(ring.coords)
    for idx in range(len(coords) - 1):
        yield LineString([coords[idx], coords[idx + 1]])


def _extract_contact_points(geometry: Any) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []

    if geometry.is_empty:
        return points

    if isinstance(geometry, Point):
        return [(float(geometry.x), float(geometry.y))]

    if geometry.geom_type == "MultiPoint":
        for point in geometry.geoms:
            points.append((float(point.x), float(point.y)))
        return points

    if geometry.geom_type in {"LineString", "LinearRing"}:
        coords = list(geometry.coords)
        if coords:
            points.append((float(coords[0][0]), float(coords[0][1])))
            points.append((float(coords[-1][0]), float(coords[-1][1])))
        return points

    if geometry.geom_type == "GeometryCollection":
        for item in geometry.geoms:
            points.extend(_extract_contact_points(item))
        return points

    return points


def _is_close_to_any(point: tuple[float, float], targets: list[tuple[float, float]], tolerance: float) -> bool:
    px, py = point
    for tx, ty in targets:
        if abs(px - tx) <= tolerance and abs(py - ty) <= tolerance:
            return True
    return False


def _segment_orientation(segment: LineString, tolerance: float) -> str:
    (x1, y1), (x2, y2) = list(segment.coords)
    dx = abs(float(x2) - float(x1))
    dy = abs(float(y2) - float(y1))
    if dx <= tolerance and dy <= tolerance:
        return "point"
    return "horizontal" if dx >= dy else "vertical"


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

    for pocket_index, pocket in enumerate(_iter_polygons(pockets)):
        diagnostics["pocket_count"] += 1
        ring = pocket.exterior
        hull_contacts = _extract_contact_points(ring.intersection(hull_boundary))

        hull_segment_orientations: set[str] = set()
        for segment in _iter_segments(ring):
            if segment.length <= float(tolerance):
                continue
            if segment.intersection(hull_boundary).length > float(tolerance):
                hull_segment_orientations.add(_segment_orientation(segment, tolerance))

        for segment in _iter_segments(ring):
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

            start_on_hull_contact = _is_close_to_any(start, hull_contacts, float(tolerance) * 10.0)
            end_on_hull_contact = _is_close_to_any(end, hull_contacts, float(tolerance) * 10.0)

            # Inward walls generally connect hull-contact point to deeper pocket boundary point.
            inward_by_endpoints = (start_on_hull_contact and not end_on_hull_contact) or (
                end_on_hull_contact and not start_on_hull_contact
            )

            if not inward_by_endpoints:
                continue

            segment_orientation = _segment_orientation(segment, tolerance)
            if hull_segment_orientations and segment_orientation in hull_segment_orientations:
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
                        "orientation": segment_orientation,
                        "x1": start[0],
                        "y1": start[1],
                        "x2": end[0],
                        "y2": end[1],
                    }
                )

    diagnostics["violating_segments"] = violating_segments
    return len(violating_segments) > 0, diagnostics

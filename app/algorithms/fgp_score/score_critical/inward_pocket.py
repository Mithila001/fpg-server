from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import unary_union

from app.algorithms.types.domain import ProcessedRoomData


Point = Tuple[float, float]


def _close_enough(a: float, b: float, tolerance: float) -> bool:
    return abs(a - b) <= float(tolerance)


def _segment_orientation(p1: Point, p2: Point, *, tolerance: float) -> str:
    x1, y1 = p1
    x2, y2 = p2
    dx = x2 - x1
    dy = y2 - y1

    if _close_enough(dx, 0.0, tolerance=tolerance) and not _close_enough(
        dy, 0.0, tolerance=tolerance
    ):
        return "vertical"
    if _close_enough(dy, 0.0, tolerance=tolerance) and not _close_enough(
        dx, 0.0, tolerance=tolerance
    ):
        return "horizontal"
    if _close_enough(dx, 0.0, tolerance=tolerance) and _close_enough(
        dy, 0.0, tolerance=tolerance
    ):
        return "zero"
    return "diagonal"


def _iter_rectilinear_segments_from_ring_coords(
    coords: Sequence[Point],
    *,
    tolerance: float,
) -> List[Tuple[Point, Point, LineString]]:
    """Extract consecutive (p1, p2) segments; skips zero-length segments."""
    segments: List[Tuple[Point, Point, LineString]] = []
    if not coords:
        return segments

    # Common shapely form: the last point repeats the first.
    if len(coords) >= 2 and _close_enough(coords[0][0], coords[-1][0], tolerance) and _close_enough(
        coords[0][1], coords[-1][1], tolerance
    ):
        coords = coords[:-1]

    if len(coords) < 2:
        return segments

    n = len(coords)
    for i in range(n):
        p1 = coords[i]
        p2 = coords[(i + 1) % n]

        x1, y1 = p1
        x2, y2 = p2
        if _close_enough(x1, x2, tolerance) and _close_enough(y1, y2, tolerance):
            continue

        seg = LineString([p1, p2])
        if float(seg.length) <= float(tolerance):
            continue
        segments.append((p1, p2, seg))

    return segments


def _iter_pocket_polygons(pockets_geom: Any) -> List[Polygon]:
    if pockets_geom is None or getattr(pockets_geom, "is_empty", True):
        return []
    if isinstance(pockets_geom, Polygon):
        return [pockets_geom]
    if isinstance(pockets_geom, MultiPolygon):
        return list(pockets_geom.geoms)
    polygons: list[Polygon] = []
    for geom in getattr(pockets_geom, "geoms", []):
        if isinstance(geom, Polygon):
            polygons.append(geom)
    return polygons


def detect_inward_pocket_violation_v2(
    post_processed_floor_plan: Sequence[ProcessedRoomData],
    *,
    max_inward_length: float = 20.0,
    tolerance: float = 1e-6,
) -> Tuple[bool, Dict[str, Any]]:
    """Detect inward pocket violations using convex-hull pockets.

    This is a standalone adaptation of the legacy `inward_pocket.py` v2 concept,
    rewritten to operate on rectilinear vertex polygons.
    """
    diagnostics: Dict[str, Any] = {
        "pocket_count": 0,
        "max_inward_segment_length": 0.0,
        "violating_segments": [],
        "threshold": float(max_inward_length),
        "tolerance": float(tolerance),
        "geometry_status": "ok",
    }

    if not post_processed_floor_plan:
        diagnostics["geometry_status"] = "no_rooms"
        return False, diagnostics

    polygons: list[Polygon] = []
    for room in post_processed_floor_plan:
        if not room.vertices or len(room.vertices) < 3:
            continue
        polygons.append(Polygon(room.vertices))

    if not polygons:
        diagnostics["geometry_status"] = "no_valid_room_polygons"
        return False, diagnostics

    union_geom = unary_union(polygons)
    if union_geom.is_empty:
        diagnostics["geometry_status"] = "empty_union"
        return False, diagnostics

    hull = union_geom.convex_hull
    pockets = hull.difference(union_geom)
    pocket_polys = _iter_pocket_polygons(pockets)
    if not pocket_polys:
        diagnostics["geometry_status"] = "no_pockets"
        return False, diagnostics

    plan_boundary = union_geom.boundary
    hull_boundary = hull.boundary

    violating_segments: list[Dict[str, Any]] = []
    overall_max_delta = 0.0

    for pocket_index, pocket in enumerate(pocket_polys):
        diagnostics["pocket_count"] = int(diagnostics["pocket_count"]) + 1

        ring_coords: list[Point] = [(float(x), float(y)) for (x, y) in pocket.exterior.coords]
        segments = _iter_rectilinear_segments_from_ring_coords(
            ring_coords, tolerance=tolerance
        )

        outer_segments: list[Tuple[Point, Point, LineString]] = []
        hull_segments: list[Tuple[Point, Point, LineString]] = []

        for p1, p2, seg in segments:
            seg_len = float(seg.length)
            if seg_len <= float(tolerance):
                continue

            on_plan = seg.intersection(plan_boundary).length > float(tolerance)
            on_hull = seg.intersection(hull_boundary).length > float(tolerance)

            if on_plan:
                outer_segments.append((p1, p2, seg))
            if on_hull:
                hull_segments.append((p1, p2, seg))

        if not hull_segments:
            continue

        horizontal_len = sum(
            float(seg.length)
            for (_p1, _p2, seg) in hull_segments
            if _segment_orientation(_p1, _p2, tolerance=tolerance) == "horizontal"
        )
        vertical_len = sum(
            float(seg.length)
            for (_p1, _p2, seg) in hull_segments
            if _segment_orientation(_p1, _p2, tolerance=tolerance) == "vertical"
        )

        convex_orientation = (
            "horizontal" if horizontal_len >= vertical_len else "vertical"
        )
        opposing_orientation = (
            "vertical" if convex_orientation == "horizontal" else "horizontal"
        )

        # "Red pocket" heuristic from legacy v2: pockets with non-standard outer segment count.
        is_red_pocket = len(outer_segments) != 2
        if not is_red_pocket:
            continue

        max_delta = 0.0
        max_segment: Tuple[Point, Point, LineString] | None = None

        for p1, p2, seg in outer_segments:
            if _segment_orientation(p1, p2, tolerance=tolerance) != opposing_orientation:
                continue

            x1, y1 = p1
            x2, y2 = p2
            if opposing_orientation == "vertical":
                delta = abs(y2 - y1)
            else:
                delta = abs(x2 - x1)

            if delta > max_delta:
                max_delta = float(delta)
                max_segment = (p1, p2, seg)

        overall_max_delta = max(overall_max_delta, float(max_delta))
        if max_segment is None:
            continue

        if max_delta > float(max_inward_length):
            (p1, p2, _seg) = max_segment
            x1, y1 = p1
            x2, y2 = p2
            violating_segments.append(
                {
                    "pocket_index": int(pocket_index),
                    "length": float(max_delta),
                    "orientation": opposing_orientation,
                    "x1": float(x1),
                    "y1": float(y1),
                    "x2": float(x2),
                    "y2": float(y2),
                }
            )

    diagnostics["violating_segments"] = violating_segments
    diagnostics["max_inward_segment_length"] = float(overall_max_delta)

    return len(violating_segments) > 0, diagnostics


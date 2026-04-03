from __future__ import annotations

from typing import Any, Iterable

from shapely.geometry import GeometryCollection, LineString, MultiPolygon, Point, Polygon


def iter_polygons(geometry: Any) -> Iterable[Polygon]:
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


def iter_segments(ring: Any) -> Iterable[LineString]:
    coords = list(ring.coords)
    for idx in range(len(coords) - 1):
        yield LineString([coords[idx], coords[idx + 1]])


def extract_contact_points(geometry: Any) -> list[tuple[float, float]]:
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
            points.extend(extract_contact_points(item))
        return points

    return points


def is_close_to_any(point: tuple[float, float], targets: list[tuple[float, float]], tolerance: float) -> bool:
    px, py = point
    for tx, ty in targets:
        if abs(px - tx) <= tolerance and abs(py - ty) <= tolerance:
            return True
    return False


def segment_orientation(segment: LineString, tolerance: float) -> str:
    (x1, y1), (x2, y2) = list(segment.coords)
    dx = abs(float(x2) - float(x1))
    dy = abs(float(y2) - float(y1))
    if dx <= tolerance and dy <= tolerance:
        return "point"
    return "horizontal" if dx >= dy else "vertical"

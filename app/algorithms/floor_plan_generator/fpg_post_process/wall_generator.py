from __future__ import annotations

from collections.abc import Iterable

from shapely.geometry import LineString, MultiLineString, Polygon, box
from shapely.ops import unary_union

from .types import NormalizedRoom, WallSegmentPayload


def _snap(value: float, tolerance: float) -> float:
    if tolerance <= 0:
        return value
    return round(value / tolerance) * tolerance


def _iter_lines(geometry: LineString | MultiLineString | Polygon) -> Iterable[LineString]:
    if isinstance(geometry, LineString):
        yield geometry
        return

    if isinstance(geometry, MultiLineString):
        for line in geometry.geoms:
            yield line
        return

    if isinstance(geometry, Polygon):
        yield LineString(geometry.exterior.coords)


def _segment_key(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> tuple[tuple[float, float], tuple[float, float]]:
    a = (x1, y1)
    b = (x2, y2)
    return (a, b) if a <= b else (b, a)


def generate_unique_wall_segments(
    rooms: list[NormalizedRoom],
    tolerance: float = 1e-6,
) -> list[WallSegmentPayload]:
    """Generate unique wall segments across all room rectangles.

    Shared boundaries between touching rooms are emitted only once.
    """
    if not rooms:
        return []

    room_polygons = [
        box(room["x"], room["y"], room["x_end"], room["y_end"])
        for room in rooms
    ]

    merged_boundaries = unary_union([poly.boundary for poly in room_polygons])

    seen: set[tuple[tuple[float, float], tuple[float, float]]] = set()
    segments: list[WallSegmentPayload] = []

    for line in _iter_lines(merged_boundaries):
        coords = list(line.coords)
        if len(coords) < 2:
            continue

        for i in range(len(coords) - 1):
            x1, y1 = coords[i]
            x2, y2 = coords[i + 1]

            sx1 = _snap(float(x1), tolerance)
            sy1 = _snap(float(y1), tolerance)
            sx2 = _snap(float(x2), tolerance)
            sy2 = _snap(float(y2), tolerance)

            if sx1 == sx2 and sy1 == sy2:
                continue

            key = _segment_key(sx1, sy1, sx2, sy2)
            if key in seen:
                continue

            seen.add(key)
            (ax, ay), (bx, by) = key
            segments.append(
                {
                    "x1": ax,
                    "y1": ay,
                    "x2": bx,
                    "y2": by,
                }
            )

    segments.sort(key=lambda s: (s["x1"], s["y1"], s["x2"], s["y2"]))
    return segments

from __future__ import annotations

from collections.abc import Iterable

from shapely.geometry import GeometryCollection, LineString, MultiLineString, Polygon

from ..types import WallSegmentPayload


def _snap(value: float, tolerance: float) -> float:
    if tolerance <= 0:
        return value
    return round(value / tolerance) * tolerance


def _iter_lines(geometry: object) -> Iterable[LineString]:
    if isinstance(geometry, LineString):
        yield geometry
        return

    if isinstance(geometry, MultiLineString):
        for line in geometry.geoms:
            yield line
        return

    if isinstance(geometry, Polygon):
        yield LineString(geometry.exterior.coords)
        return

    if isinstance(geometry, GeometryCollection):
        for item in geometry.geoms:
            yield from _iter_lines(item)


def _segment_key(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> tuple[tuple[float, float], tuple[float, float]]:
    a = (x1, y1)
    b = (x2, y2)
    return (a, b) if a <= b else (b, a)


def extract_unique_segments(geometry: object, tolerance: float = 1e-6) -> list[WallSegmentPayload]:
    """Convert any line-like geometry into sorted unique wall segments."""
    seen: set[tuple[tuple[float, float], tuple[float, float]]] = set()
    segments: list[WallSegmentPayload] = []

    for line in _iter_lines(geometry):
        coords = list(line.coords)
        if len(coords) < 2:
            continue

        for index in range(len(coords) - 1):
            x1, y1 = coords[index]
            x2, y2 = coords[index + 1]

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

    segments.sort(key=lambda segment: (segment["x1"], segment["y1"], segment["x2"], segment["y2"]))
    return segments

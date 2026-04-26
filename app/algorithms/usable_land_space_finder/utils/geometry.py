from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

EPS = 1e-9
Point = tuple[float, float]


def to_open_polygon_tuples(raw_points: Sequence[Mapping[str, Any]]) -> list[Point]:
    points = [(point["x"], point["y"]) for point in raw_points]
    if len(points) > 1 and points[0] == points[-1]:
        points = points[:-1]
    return points


def polygon_area(polygon: list[Point]) -> float:
    if len(polygon) < 3:
        return 0.0

    twice_area = 0.0
    size = len(polygon)
    for index in range(size):
        x1, y1 = polygon[index]
        x2, y2 = polygon[(index + 1) % size]
        twice_area += (x1 * y2) - (x2 * y1)
    return abs(twice_area) / 2.0


def signed_polygon_area(polygon: list[Point]) -> float:
    twice_area = 0.0
    size = len(polygon)
    for index in range(size):
        x1, y1 = polygon[index]
        x2, y2 = polygon[(index + 1) % size]
        twice_area += (x1 * y2) - (x2 * y1)
    return twice_area / 2.0


def _is_ccw(polygon: list[Point]) -> bool:
    return signed_polygon_area(polygon) > 0


def is_polygon_ccw(polygon: list[Point]) -> bool:
    return signed_polygon_area(polygon) > 0


def _unit_vector(dx: float, dy: float) -> Point:
    magnitude = math.hypot(dx, dy)
    if magnitude <= EPS:
        raise ValueError("Degenerate segment with zero length found.")
    return dx / magnitude, dy / magnitude


def inward_normal(start: Point, end: Point, is_ccw: bool) -> Point:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    ux, uy = _unit_vector(dx, dy)

    if is_ccw:
        return -uy, ux
    return uy, -ux


def ensure_convex_polygon(polygon: list[Point]) -> None:
    if len(polygon) < 3:
        raise ValueError("A polygon requires at least 3 points.")

    orientation = 0
    size = len(polygon)
    for index in range(size):
        p0 = polygon[index]
        p1 = polygon[(index + 1) % size]
        p2 = polygon[(index + 2) % size]

        edge1 = (p1[0] - p0[0], p1[1] - p0[1])
        edge2 = (p2[0] - p1[0], p2[1] - p1[1])
        cross = (edge1[0] * edge2[1]) - (edge1[1] * edge2[0])

        if abs(cross) <= EPS:
            continue

        current = 1 if cross > 0 else -1
        if orientation == 0:
            orientation = current
        elif orientation != current:
            raise ValueError("The polygon must be convex.")

    if orientation == 0:
        raise ValueError("Polygon points are collinear; valid convex polygon required.")


def _line_intersection(n1: Point, c1: float, n2: Point, c2: float) -> Point:
    a1, b1 = n1
    a2, b2 = n2
    determinant = (a1 * b2) - (a2 * b1)
    if abs(determinant) <= EPS:
        raise ValueError("Shrink failed due to near-parallel offset lines.")

    x = ((c1 * b2) - (c2 * b1)) / determinant
    y = ((a1 * c2) - (a2 * c1)) / determinant

    if not (math.isfinite(x) and math.isfinite(y)):
        raise ValueError("Shrink failed due to non-finite intersection coordinates.")

    return x, y


def shrink_convex_polygon(polygon: list[Point], offsets: list[float]) -> list[Point]:
    if len(polygon) != len(offsets):
        raise ValueError("Offsets must be provided per boundary segment.")

    is_ccw = _is_ccw(polygon)
    normals: list[Point] = []
    constants: list[float] = []
    size = len(polygon)

    for index in range(size):
        start = polygon[index]
        end = polygon[(index + 1) % size]
        normal = inward_normal(start, end, is_ccw)
        c_val = (normal[0] * start[0]) + (normal[1] * start[1]) + offsets[index]
        normals.append(normal)
        constants.append(c_val)

    result: list[Point] = []
    for index in range(size):
        n1 = normals[index]
        c1 = constants[index]
        n2 = normals[(index + 1) % size]
        c2 = constants[(index + 1) % size]
        result.append(_line_intersection(n1, c1, n2, c2))

    return result

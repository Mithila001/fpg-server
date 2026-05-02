from __future__ import annotations

from typing import Iterable, Sequence, Tuple

from app.algorithms.types.domain import ProcessedRoomData

Point = Tuple[float, float]


def _close_enough(a: Point, b: Point, tolerance: float) -> bool:
    return abs(a[0] - b[0]) <= tolerance and abs(a[1] - b[1]) <= tolerance


def _polygon_area(vertices: Sequence[Point]) -> float:
    """Shoelace area. Assumes vertices are ordered and already closed or will be treated as closed."""
    if len(vertices) < 3:
        return 0.0

    # Use the standard loop without assuming the last vertex repeats the first.
    area2 = 0.0
    n = len(vertices)
    for i in range(n):
        j = (i + 1) % n
        area2 += vertices[i][0] * vertices[j][1]
        area2 -= vertices[j][0] * vertices[i][1]
    return abs(area2) / 2.0


def _is_rectilinear_polygon_vertices(
    vertices: Sequence[Tuple[float, float]],
    *,
    tolerance: float,
) -> bool:
    if not vertices:
        return False

    # Convert once so we don't repeatedly index tuples of unknown numeric types.
    pts: list[Point] = [(float(x), float(y)) for (x, y) in vertices]
    if len(pts) < 4:
        # For a valid closed rectilinear polygon, we expect >= 4 points
        # (typically: 4 corners + a repeated start corner).
        return False

    first = pts[0]
    last = pts[-1]
    if not _close_enough(first, last, tolerance=tolerance):
        # `extend_floor_plan_walls` typically emits shapely exterior coords
        # where the first point is repeated at the end. If that doesn't hold,
        # rectilinear “polygon walls” become ambiguous.
        return False

    # For edge validation, we include the closing edge by iterating over the
    # original vertices list (which includes the duplicate closing point).
    # For area computation, avoid double-counting the duplicate closing vertex.
    pts_no_close: list[Point]
    if len(pts) >= 2 and _close_enough(pts[-1], pts[0], tolerance=tolerance):
        pts_no_close = pts[:-1]
    else:
        pts_no_close = pts

    if len(pts_no_close) < 3:
        return False

    area = _polygon_area(pts_no_close)
    if area <= float(tolerance):
        return False

    # Validate each consecutive edge is axis-aligned (vertical or horizontal).
    # - Ignore zero-length edges (can happen if there are repeated vertices).
    # - Fail on diagonal edges where both dx and dy are non-trivial.
    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        dx = x2 - x1
        dy = y2 - y1

        if abs(dx) <= tolerance and abs(dy) <= tolerance:
            # Zero-length segment -> ignore.
            continue

        is_vertical = abs(dx) <= tolerance and abs(dy) > tolerance
        is_horizontal = abs(dy) <= tolerance and abs(dx) > tolerance
        if not (is_vertical or is_horizontal):
            return False

    return True


def verify_post_processed_floor_plan(
    post_processed_floor_plan: Sequence[ProcessedRoomData],
    tolerance: float = 1e-6,
) -> bool:
    """Verify that post-processed room polygons are rectilinear.

    The expected representation is axis-aligned polygons encoded as a sequence
    of `(x, y)` vertices where the last vertex equals the first vertex.
    """
    if not post_processed_floor_plan:
        return False

    for room in post_processed_floor_plan:
        if not isinstance(room, ProcessedRoomData):
            # Be strict: callers should pass real ProcessedRoomData objects.
            return False

        if not _is_rectilinear_polygon_vertices(room.vertices, tolerance=tolerance):
            return False

    return True


from __future__ import annotations

from time import perf_counter
from typing import Any

from app.algorithms.fp_boundary_finder import FPBoundaryFinder
from app.algorithms.usable_land_space_finder import find_usable_land_space


def _error_payload(message: str, status: str = "ERROR") -> dict[str, Any]:
    return {
        "status": status,
        "message": message,
        "buildable_rectangle": None,
        "shrunk_boundary": None,
        "metadata": None,
    }


def _extract_polygon_coordinates(
    land_data: dict[str, Any],
) -> list[tuple[float, float]]:
    raw_points = [
        (point["x"], point["y"])
        for point in land_data.get("segmentsCoordinates", [])
        if "x" in point and "y" in point
    ]

    if len(raw_points) < 3:
        raise ValueError("At least 3 land boundary points are required.")

    # Remove duplicated closing coordinate if present.
    if len(raw_points) > 1 and raw_points[0] == raw_points[-1]:
        raw_points = raw_points[:-1]

    if len(raw_points) < 3:
        raise ValueError("Boundary points are invalid after normalization.")

    return raw_points


def _extract_ta_line(
    land_data: dict[str, Any],
) -> tuple[tuple[float, float], tuple[float, float]]:
    roads = land_data.get("roadConnected", [])
    for road in roads:
        segment = road.get("segment", [])
        if len(segment) >= 2:
            return (
                (segment[0]["x"], segment[0]["y"]),
                (segment[1]["x"], segment[1]["y"]),
            )

    raise ValueError("No valid TA segment found in land data.")


def _normalize_vector(vector: tuple[float, float]) -> tuple[float, float] | None:
    dx, dy = vector
    length = (dx * dx + dy * dy) ** 0.5
    if length <= 1e-9:
        return None
    return (dx / length, dy / length)


def _point_line_distance(
    point: tuple[float, float], line: tuple[tuple[float, float], tuple[float, float]]
) -> float:
    (x0, y0) = point
    (x1, y1), (x2, y2) = line
    dx = x2 - x1
    dy = y2 - y1
    denom = (dx * dx + dy * dy) ** 0.5
    if denom <= 1e-9:
        return 0.0
    return abs(dy * x0 - dx * y0 + x2 * y1 - y2 * x1) / denom


def _build_edge_payload(
    edge: tuple[tuple[float, float], tuple[float, float]],
) -> list[dict[str, float]]:
    return [
        {"x": edge[0][0], "y": edge[0][1]},
        {"x": edge[1][0], "y": edge[1][1]},
    ]


def _rectangle_sides_payload(
    best_rectangle: list[tuple[float, float]],
    ta_line: tuple[tuple[float, float], tuple[float, float]],
) -> dict[str, list[dict[str, float]]] | None:
    if len(best_rectangle) < 4:
        return None

    vertices = best_rectangle
    edges = [
        (vertices[i], vertices[(i + 1) % len(vertices)]) for i in range(len(vertices))
    ]

    ta_vector = (ta_line[1][0] - ta_line[0][0], ta_line[1][1] - ta_line[0][1])
    ta_unit = _normalize_vector(ta_vector)
    if ta_unit is None:
        return None

    edge_scores: list[tuple[int, float]] = []
    for idx, (start, end) in enumerate(edges):
        edge_vector = (end[0] - start[0], end[1] - start[1])
        edge_unit = _normalize_vector(edge_vector)
        if edge_unit is None:
            edge_scores.append((idx, -1.0))
            continue
        dot = abs(edge_unit[0] * ta_unit[0] + edge_unit[1] * ta_unit[1])
        edge_scores.append((idx, dot))

    edge_scores.sort(key=lambda item: item[1], reverse=True)
    if len(edge_scores) < 2 or edge_scores[0][1] < 0:
        return None

    parallel_indices = [edge_scores[0][0], edge_scores[1][0]]
    parallel_edges = [edges[parallel_indices[0]], edges[parallel_indices[1]]]

    distances = []
    for edge in parallel_edges:
        midpoint = (
            (edge[0][0] + edge[1][0]) / 2.0,
            (edge[0][1] + edge[1][1]) / 2.0,
        )
        distances.append(_point_line_distance(midpoint, ta_line))

    if distances[0] <= distances[1]:
        front_edge = parallel_edges[0]
        back_edge = parallel_edges[1]
    else:
        front_edge = parallel_edges[1]
        back_edge = parallel_edges[0]

    front_vector = (
        front_edge[1][0] - front_edge[0][0],
        front_edge[1][1] - front_edge[0][1],
    )
    front_unit = _normalize_vector(front_vector)
    if front_unit is None:
        return None

    center = (
        sum(point[0] for point in vertices) / len(vertices),
        sum(point[1] for point in vertices) / len(vertices),
    )

    remaining_edges = [edge for edge in edges if edge not in (front_edge, back_edge)]
    if len(remaining_edges) != 2:
        return None

    left_edge = None
    right_edge = None
    for edge in remaining_edges:
        midpoint = (
            (edge[0][0] + edge[1][0]) / 2.0,
            (edge[0][1] + edge[1][1]) / 2.0,
        )
        to_mid = (midpoint[0] - center[0], midpoint[1] - center[1])
        cross = front_unit[0] * to_mid[1] - front_unit[1] * to_mid[0]
        if cross >= 0:
            left_edge = edge
        else:
            right_edge = edge

    if left_edge is None or right_edge is None:
        return None

    return {
        "front": _build_edge_payload(front_edge),
        "back": _build_edge_payload(back_edge),
        "left": _build_edge_payload(left_edge),
        "right": _build_edge_payload(right_edge),
    }


def _rectangle_payload(
    best_rectangle: list[tuple[float, float]],
    ta_line: tuple[tuple[float, float], tuple[float, float]],
) -> dict[str, Any] | None:
    if not best_rectangle:
        return None

    xs = [point[0] for point in best_rectangle]
    ys = [point[1] for point in best_rectangle]
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)

    if width <= 0 or height <= 0:
        return None

    sides = _rectangle_sides_payload(best_rectangle, ta_line)

    return {
        "vertices": [{"x": point[0], "y": point[1]} for point in best_rectangle],
        "width": width,
        "height": height,
        "area": width * height,
        "sides": sides,
    }


def run_buildable_space_pipeline(
    land_data: dict[str, Any],
    min_width: float = 100,
    min_height: float = 100,
    should_plot: bool = False,
) -> dict[str, Any]:
    """Compute buildable space from API land payload and return normalized response payload."""
    start_time = perf_counter()

    try:
        raw_polygon_coordinates = _extract_polygon_coordinates(land_data)
        ta_line = _extract_ta_line(land_data)

        usable_land_result = find_usable_land_space(land_data)
        shrunk_polygon_coordinates = [
            (point["x"], point["y"])
            for point in usable_land_result.get("shrunkSegmentsCoordinates", [])
        ]

        finder = FPBoundaryFinder()
        best_rectangle = finder.fp_boundary_finder(
            polygon_coordinates=shrunk_polygon_coordinates,
            TA_line=ta_line,
            min_width=min_width,
            min_height=min_height,
        )

        rectangle = _rectangle_payload(best_rectangle, ta_line)
        if rectangle is None:
            status = "OK"
            message = (
                "Buildable space computed, but no feasible rectangle met constraints."
            )
        else:
            status = "OK"
            message = "Buildable space computed successfully."

        payload = {
            "status": status,
            "message": message,
            "buildable_rectangle": rectangle,
            "shrunk_boundary": usable_land_result.get("shrunkSegmentsCoordinates", []),
            "metadata": usable_land_result.get("metadata"),
        }

        duration_ms = (perf_counter() - start_time) * 1000
        return payload

    except ValueError as exc:
        duration_ms = (perf_counter() - start_time) * 1000
        return _error_payload(str(exc))
    except Exception as exc:
        duration_ms = (perf_counter() - start_time) * 1000

        return _error_payload("Unexpected error while computing buildable space.")

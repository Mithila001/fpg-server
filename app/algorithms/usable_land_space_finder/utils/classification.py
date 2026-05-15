from __future__ import annotations

import math
from typing import cast

from ..types.land_types import RoadConnectedPayload, SegmentCategory
from .geometry import Point, inward_normal, is_polygon_ccw

EPS = 1e-6

# Offsets are defined in solver units (10 units = 1 meter).
# Default Always apply the base direction offset, then add any applicable road setback.
DIRECTION_OFFSETS: dict[SegmentCategory, float] = {
    "front": 10.0,
    "back": 30,
    "left": 10,
    "right": 10,
}

ROAD_SETBACKS: dict[str, dict[SegmentCategory, float]] = {
    "mainRoad": {
        "front": 5,
        "back": 0,
        "left": 5,
        "right": 5,
    },
    "privateRoad": {
        "front": 5.0,
        "back": 0,
        "left": 0,
        "right": 0,
    },
}

CATEGORIES: list[SegmentCategory] = ["front", "back", "left", "right"]


def _points_equal(p1: Point, p2: Point) -> bool:
    return abs(p1[0] - p2[0]) <= EPS and abs(p1[1] - p2[1]) <= EPS


def _edge_matches(edge_start: Point, edge_end: Point, p1: Point, p2: Point) -> bool:
    return (_points_equal(edge_start, p1) and _points_equal(edge_end, p2)) or (
        _points_equal(edge_start, p2) and _points_equal(edge_end, p1)
    )


def _build_segments(polygon: list[Point]) -> list[tuple[Point, Point]]:
    return [
        (polygon[index], polygon[(index + 1) % len(polygon)])
        for index in range(len(polygon))
    ]


def _find_segment_index(
    segments: list[tuple[Point, Point]],
    p1: Point,
    p2: Point,
) -> int | None:
    for index, (start, end) in enumerate(segments):
        if _edge_matches(start, end, p1, p2):
            return index
    return None


def _unit_vector(dx: float, dy: float) -> Point:
    magnitude = math.hypot(dx, dy)
    if magnitude <= EPS:
        raise ValueError("TA segment is degenerate.")
    return dx / magnitude, dy / magnitude


def _dot(a: Point, b: Point) -> float:
    return (a[0] * b[0]) + (a[1] * b[1])


def _segment_scores(
    segment_normal: Point,
    ta_tangent: Point,
    front_normal: Point,
) -> dict[SegmentCategory, float]:
    targets: dict[SegmentCategory, Point] = {
        "front": front_normal,
        "back": (-front_normal[0], -front_normal[1]),
        "left": ta_tangent,
        "right": (-ta_tangent[0], -ta_tangent[1]),
    }
    return {
        category: _dot(segment_normal, target) for category, target in targets.items()
    }


def _ensure_all_categories(
    assignments: list[SegmentCategory],
    score_table: list[dict[SegmentCategory, float]],
    ta_segment_index: int,
) -> list[SegmentCategory]:
    counts = {category: assignments.count(category) for category in CATEGORIES}

    while True:
        missing: list[SegmentCategory] = [
            category for category in CATEGORIES if counts[category] == 0
        ]
        if not missing:
            return assignments

        changed = False
        for category in missing:
            candidate_index: int | None = None
            candidate_score = float("-inf")

            for index, current_category in enumerate(assignments):
                if index == ta_segment_index:
                    continue
                if counts[current_category] <= 1:
                    continue

                score = score_table[index][category]
                if score > candidate_score:
                    candidate_score = score
                    candidate_index = index

            if candidate_index is None:
                continue

            old_category = assignments[candidate_index]
            assignments[candidate_index] = category
            counts[old_category] -= 1
            counts[category] += 1
            changed = True

        if not changed:
            raise ValueError(
                "Unable to assign at least one segment to each of front/back/left/right."
            )


def _road_offset_by_segment(
    segments: list[tuple[Point, Point]],
    assignments: list[SegmentCategory],
    roads: list[RoadConnectedPayload],
) -> list[float]:
    road_offsets = [0.0] * len(segments)

    for road in roads:
        road_type = road.get("roadType")
        setbacks = ROAD_SETBACKS.get(road_type or "")
        if setbacks is None:
            supported = ", ".join(sorted(ROAD_SETBACKS))
            raise ValueError(
                f"Unsupported road type: {road_type}. Supported: {supported}"
            )

        road_segment = road.get("segment", [])
        if len(road_segment) < 2:
            raise ValueError("Each roadConnected item must include a 2-point segment.")

        p1 = (road_segment[0]["x"], road_segment[0]["y"])
        p2 = (road_segment[1]["x"], road_segment[1]["y"])
        segment_index = _find_segment_index(segments, p1, p2)
        if segment_index is None:
            raise ValueError(
                "A roadConnected segment does not match any boundary segment."
            )

        category = assignments[segment_index]
        road_offsets[segment_index] += setbacks.get(category, 0.0)

    return road_offsets


def classify_segments_and_offsets(
    polygon: list[Point],
    ta_segment: tuple[Point, Point],
    roads: list[RoadConnectedPayload],
) -> tuple[list[SegmentCategory], list[float]]:
    if len(polygon) < 4:
        raise ValueError(
            "At least 4 polygon edges are required for side categorization."
        )

    segments = _build_segments(polygon)
    ta_segment_index = _find_segment_index(segments, ta_segment[0], ta_segment[1])
    if ta_segment_index is None:
        raise ValueError("TA segment is not found on polygon boundary.")

    is_ccw = is_polygon_ccw(polygon)
    ta_start, ta_end = segments[ta_segment_index]
    ta_tangent = _unit_vector(ta_end[0] - ta_start[0], ta_end[1] - ta_start[1])
    front_normal = inward_normal(ta_start, ta_end, is_ccw)

    score_table: list[dict[SegmentCategory, float]] = []
    assignments: list[SegmentCategory] = []

    for segment in segments:
        normal = inward_normal(segment[0], segment[1], is_ccw)
        scores = _segment_scores(normal, ta_tangent, front_normal)
        category = cast(SegmentCategory, max(scores, key=lambda item: scores[item]))
        assignments.append(category)
        score_table.append(scores)

    assignments[ta_segment_index] = "front"
    assignments = _ensure_all_categories(assignments, score_table, ta_segment_index)

    road_offsets = _road_offset_by_segment(segments, assignments, roads)
    final_offsets = [
        DIRECTION_OFFSETS[assignments[index]] + road_offsets[index]
        for index in range(len(assignments))
    ]

    return assignments, final_offsets

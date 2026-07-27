"""Public API for usable land space shrinking."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .types.land_types import (
    CoordinatePayload,
    SegmentCategory,
    SegmentCategoryItem,
    SegmentOffsetItem,
    UsableLandMetadata,
    UsableLandSpaceResult,
)
from .utils.classification import classify_segments_and_offsets
from .utils.geometry import (
    ensure_convex_polygon,
    polygon_area,
    shrink_convex_polygon,
    to_open_polygon_tuples,
)

__all__ = ["find_usable_land_space"]


def _extract_ta_segment(
    land_data: Mapping[str, Any],
) -> tuple[CoordinatePayload, CoordinatePayload]:
    roads = land_data.get("roadConnected", [])
    if not roads:
        raise ValueError("roadConnected cannot be empty; TA segment is required.")

    ta_segment = roads[0].get("segment", [])
    if len(ta_segment) < 2:
        raise ValueError("TA segment requires 2 points in roadConnected[0].segment.")

    return ta_segment[0], ta_segment[1]


def _build_metadata(
    categories: list[SegmentCategory],
    final_offsets: list[float],
) -> UsableLandMetadata:
    segment_categories: list[SegmentCategoryItem] = [
        {"index": index, "category": category}
        for index, category in enumerate(categories)
    ]
    segment_final_offsets: list[SegmentOffsetItem] = [
        {"index": index, "offset": offset} for index, offset in enumerate(final_offsets)
    ]

    return {
        "segmentCategories": segment_categories,
        "segmentFinalOffsets": segment_final_offsets,
    }


def find_usable_land_space(land_data: Mapping[str, Any]) -> UsableLandSpaceResult:
    """Shrink a convex land polygon based on direction and road-aware offsets.

    Rules:
    - TA segment is always treated as front.
    - Every segment gets a direction offset by category.
    - Road-connected segments receive additional road-type offsets.
    - If shrinking creates invalid geometry, a ValueError is raised.
    """
    polygon = to_open_polygon_tuples(land_data.get("segmentsCoordinates", []))
    if len(polygon) < 4:
        raise ValueError(
            "At least 4 boundary points are required for side categorization."
        )

    ensure_convex_polygon(polygon)

    ta_start, ta_end = _extract_ta_segment(land_data)
    categories, final_offsets = classify_segments_and_offsets(
        polygon=polygon,
        ta_segment=(
            (ta_start["x"], ta_start["y"]),
            (ta_end["x"], ta_end["y"]),
        ),
        roads=land_data.get("roadConnected", []),
    )

    shrunk_polygon = shrink_convex_polygon(polygon, final_offsets)
    ensure_convex_polygon(shrunk_polygon)

    if polygon_area(shrunk_polygon) <= 0:
        raise ValueError(
            "Shrinking is too aggressive: resulting polygon area is not positive."
        )

    return {
        "shrunkSegmentsCoordinates": [
            {"x": point[0], "y": point[1]} for point in shrunk_polygon
        ],
        "metadata": _build_metadata(categories, final_offsets),
    }

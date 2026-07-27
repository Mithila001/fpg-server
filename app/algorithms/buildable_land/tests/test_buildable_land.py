from __future__ import annotations

from dataclasses import replace

import pytest

from app.algorithms.buildable_land import (
    BuildableLandError,
    calculate_buildable_land,
    normalize_land_request,
)
from app.algorithms.types_new import (
    BuildableSpaceErrorCode,
    BuildableSpaceRequestData,
    Point,
    Polygon,
    RoadAttachment,
    RoadRole,
    RoadType,
)
from app.pipeline.buildable_space import load_buildable_space_reference_data


def _request(
    points: tuple[tuple[int, int], ...],
    *,
    road_edge: int = 0,
) -> BuildableSpaceRequestData:
    return BuildableSpaceRequestData(
        land_boundary=Polygon(tuple(Point(x, y) for x, y in points)),
        roads=(
            RoadAttachment(
                boundary_edge_index=road_edge,
                role=RoadRole.MAIN_ENTRY,
                road_type=RoadType.MAIN_ROAD,
            ),
        ),
    )


def test_square_setbacks_are_composed_and_clipped() -> None:
    reference = load_buildable_space_reference_data()
    land = normalize_land_request(
        _request(((0, 0), (200, 0), (200, 200), (0, 200))),
        reference,
    )

    result = calculate_buildable_land(land, reference.active_profile)

    assert result.area == pytest.approx(180 * 155)
    assert {(round(point.x), round(point.y)) for point in result.boundary.points} == {
        (10, 15),
        (190, 15),
        (190, 170),
        (10, 170),
    }
    setbacks = {item.edge_index: item for item in result.edge_setbacks}
    assert setbacks[0].final_setback == 15
    assert setbacks[0].road_type is RoadType.MAIN_ROAD
    assert setbacks[2].final_setback == 30


def test_clockwise_normalization_retains_client_edge_indexes() -> None:
    reference = load_buildable_space_reference_data()
    land = normalize_land_request(
        _request(
            ((0, 0), (0, 200), (200, 200), (200, 0)),
            road_edge=3,
        ),
        reference,
    )

    result = calculate_buildable_land(land, reference.active_profile)

    front = next(item for item in result.edge_setbacks if item.road_type is not None)
    assert front.edge_index == 3
    assert front.final_setback == 15


def test_closed_polygon_is_accepted_but_collinear_vertex_is_rejected() -> None:
    reference = load_buildable_space_reference_data()
    closed = _request(((0, 0), (200, 0), (200, 200), (0, 200), (0, 0)))
    assert len(normalize_land_request(closed, reference).boundary.points) == 4

    collinear = _request(((0, 0), (100, 0), (200, 0), (200, 200), (0, 200)))
    with pytest.raises(BuildableLandError) as caught:
        normalize_land_request(collinear, reference)
    assert caught.value.code is BuildableSpaceErrorCode.INVALID_LAND_BOUNDARY


def test_concave_polygon_is_rejected() -> None:
    reference = load_buildable_space_reference_data()
    request = _request(((0, 0), (200, 0), (100, 50), (200, 200), (0, 200)))

    with pytest.raises(BuildableLandError) as caught:
        normalize_land_request(request, reference)

    assert caught.value.code is BuildableSpaceErrorCode.NON_CONVEX_LAND


def test_excessive_setbacks_eliminate_land() -> None:
    reference = load_buildable_space_reference_data()
    profile = replace(
        reference.active_profile,
        base_setbacks={
            side: 500 for side in reference.active_profile.base_setbacks
        },
    )
    land = normalize_land_request(
        _request(((0, 0), (200, 0), (200, 200), (0, 200))),
        reference,
    )

    with pytest.raises(BuildableLandError) as caught:
        calculate_buildable_land(land, profile)

    assert (
        caught.value.code
        is BuildableSpaceErrorCode.SETBACK_ELIMINATES_BUILDABLE_LAND
    )

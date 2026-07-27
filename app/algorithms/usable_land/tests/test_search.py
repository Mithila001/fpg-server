# from __future__ import annotations

# import pytest
# from shapely.geometry import Polygon as ShapelyPolygon

# from app.algorithms.buildable_land import (
#     calculate_buildable_land,
#     normalize_land_request,
# )
# from app.algorithms.types_new import (
#     BuildableSpaceErrorCode,
#     BuildableSpaceRequestData,
#     FloorWidthAlignment,
#     Point,
#     Polygon,
#     RoadAttachment,
#     RoadRole,
#     RoadType,
#     UsableLandConstraints,
# )
# from app.algorithms.usable_land import UsableLandError, find_usable_land
# from app.algorithms.usable_land.search import find_best_local_rectangle
# from app.pipeline.buildable_space import load_buildable_space_reference_data


# def _land() -> tuple[object, object, object]:
#     reference = load_buildable_space_reference_data()
#     request = BuildableSpaceRequestData(
#         land_boundary=Polygon(
#             (
#                 Point(0, 0),
#                 Point(200, 0),
#                 Point(200, 200),
#                 Point(0, 200),
#             )
#         ),
#         roads=(
#             RoadAttachment(
#                 boundary_edge_index=0,
#                 role=RoadRole.MAIN_ENTRY,
#                 road_type=RoadType.MAIN_ROAD,
#             ),
#         ),
#     )
#     land = normalize_land_request(request, reference)
#     buildable = calculate_buildable_land(land, reference.active_profile)
#     return reference, land, buildable


# def test_rectangle_is_snapped_contained_and_deterministic() -> None:
#     reference, land, buildable = _land()

#     first = find_usable_land(
#         buildable,
#         land,
#         reference.usable_land_constraints,
#     )
#     second = find_usable_land(
#         buildable,
#         land,
#         reference.usable_land_constraints,
#     )

#     assert first == second
#     assert first.width == 180
#     assert first.length == 155
#     assert first.area == first.width * first.length
#     assert (
#         first.floor_width_alignment
#         is FloorWidthAlignment.PARALLEL_TO_ENTRY_ROAD
#     )
#     buildable_shape = ShapelyPolygon(
#         [(point.x, point.y) for point in buildable.boundary.points]
#     )
#     usable_shape = ShapelyPolygon(
#         [(point.x, point.y) for point in first.boundary.points]
#     )
#     assert buildable_shape.buffer(1e-6).covers(usable_shape)


# def test_search_limit_is_enforced_before_pair_search() -> None:
#     polygon = Polygon(
#         (
#             Point(0, 0),
#             Point(100, 0),
#             Point(100, 6000),
#             Point(0, 6000),
#         )
#     )
#     constraints = UsableLandConstraints(
#         minimum_width=80,
#         minimum_length=80,
#         search_resolution=5,
#         maximum_sweep_lines=1000,
#     )

#     with pytest.raises(UsableLandError) as caught:
#         find_best_local_rectangle(polygon, constraints)

#     assert caught.value.code is BuildableSpaceErrorCode.SEARCH_LIMIT_EXCEEDED
#     assert caught.value.details["maximum_sweep_lines"] == 1000

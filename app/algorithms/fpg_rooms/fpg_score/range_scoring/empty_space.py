# from __future__ import annotations

# from typing import Any, Dict, Sequence, Tuple

# from shapely.geometry import MultiPolygon, Polygon, box
# from shapely.ops import unary_union


# def score_empty_space(
#     solution: Sequence[Dict[str, Any]],
#     floor_width: float,
#     floor_height: float,
#     wall_union: Dict[str, Any] | None = None,
#     tolerance: float = 1e-6,
# ) -> Tuple[float, Dict[str, float]]:
#     """Shapely empty-space score based on enclosed air-gaps.

#     The score now acts as a geometric gate signal:
#     - no enclosed air-gap => score 100
#     - enclosed air-gap exists => score 1
#     """
#     _ = wall_union
#     if not solution:
#         return 1.0, {
#             "has_air_gap": 1.0,
#             "air_gap_area": 0.0,
#             "boundary_area": 0.0,
#             "union_area": 0.0,
#             "floor_area": 0.0,
#             "tolerance": float(tolerance),
#             "geometry_valid": 0.0,
#         }

#     room_polygons = [
#         box(
#             float(room["x"]),
#             float(room["y"]),
#             float(room["x_end"]),
#             float(room["y_end"]),
#         )
#         for room in solution
#     ]
#     union_shape = unary_union(room_polygons)

#     if union_shape.is_empty:
#         return 1.0, {
#             "has_air_gap": 1.0,
#             "air_gap_area": 0.0,
#             "boundary_area": 0.0,
#             "union_area": 0.0,
#             "floor_area": float(max(1.0, floor_width * floor_height)),
#             "tolerance": float(tolerance),
#             "geometry_valid": 0.0,
#         }

#     if isinstance(union_shape, Polygon):
#         boundary_shape = Polygon(union_shape.exterior)
#     elif isinstance(union_shape, MultiPolygon):
#         boundary_shape = MultiPolygon([Polygon(poly.exterior) for poly in union_shape.geoms])
#     else:
#         # Fallback for uncommon geometry collections from union operations.
#         polygons = [geom for geom in getattr(union_shape, "geoms", []) if isinstance(geom, Polygon)]
#         if not polygons:
#             return 1.0, {
#                 "has_air_gap": 1.0,
#                 "air_gap_area": 0.0,
#                 "boundary_area": 0.0,
#                 "union_area": 0.0,
#                 "floor_area": float(max(1.0, floor_width * floor_height)),
#                 "tolerance": float(tolerance),
#                 "geometry_valid": 0.0,
#             }
#         boundary_shape = MultiPolygon([Polygon(poly.exterior) for poly in polygons])

#     air_gaps = boundary_shape.difference(union_shape)
#     air_gap_area = float(max(0.0, air_gaps.area))
#     has_air_gap = air_gap_area > float(tolerance)

#     return (1.0 if has_air_gap else 100.0), {
#         "has_air_gap": 1.0 if has_air_gap else 0.0,
#         "air_gap_area": air_gap_area,
#         "boundary_area": float(max(0.0, boundary_shape.area)),
#         "union_area": float(max(0.0, union_shape.area)),
#         "floor_area": float(max(1.0, floor_width * floor_height)),
#         "tolerance": float(tolerance),
#         "geometry_valid": 1.0,
#     }

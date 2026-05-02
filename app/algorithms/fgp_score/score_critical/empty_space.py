from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from shapely.geometry import MultiPolygon, Polygon, box
from shapely.ops import unary_union

from app.algorithms.types.domain import ProcessedRoomData


def _boundary_from_union(union_shape: Any) -> Any:
    """Convert union geometry to a geometry representing its exterior boundary(s)."""
    if isinstance(union_shape, Polygon):
        return Polygon(union_shape.exterior)

    if isinstance(union_shape, MultiPolygon):
        return MultiPolygon([Polygon(poly.exterior) for poly in union_shape.geoms])

    polygons = [geom for geom in getattr(union_shape, "geoms", []) if isinstance(geom, Polygon)]
    if not polygons:
        return None
    return MultiPolygon([Polygon(poly.exterior) for poly in polygons])


def validate_empty_space(
    post_processed_floor_plan: Sequence[ProcessedRoomData],
    floor_width: float,
    floor_height: float,
    *,
    tolerance: float = 1e-6,
) -> Tuple[List[str], Dict[str, Any]]:
    """Validate that there are no enclosed air-gaps in room coverage.

    Returns:
      (violations, diagnostics)
    """
    diagnostics: Dict[str, Any] = {
        "has_air_gap": 0.0,
        "air_gap_area": 0.0,
        "boundary_area": 0.0,
        "union_area": 0.0,
        "floor_area": float(max(1.0, float(floor_width) * float(floor_height))),
        "tolerance": float(tolerance),
        "geometry_valid": 0.0,
    }

    if not post_processed_floor_plan:
        diagnostics["geometry_valid"] = 0.0
        return ["Empty solution triggers empty-space validation failure"], diagnostics

    room_polygons: list[Polygon] = []
    for room in post_processed_floor_plan:
        if not room.vertices or len(room.vertices) < 3:
            continue
        room_polygons.append(Polygon(room.vertices))

    if not room_polygons:
        diagnostics["geometry_valid"] = 0.0
        return ["No valid room polygons found in empty-space validation"], diagnostics

    union_shape = unary_union(room_polygons)
    if union_shape.is_empty:
        diagnostics["geometry_valid"] = 0.0
        return ["Union of rooms is empty in empty-space validation"], diagnostics

    boundary_shape = _boundary_from_union(union_shape)
    if boundary_shape is None:
        diagnostics["geometry_valid"] = 0.0
        return ["Unsupported union geometry in empty-space validation"], diagnostics

    air_gaps = boundary_shape.difference(union_shape)
    air_gap_area = float(max(0.0, air_gaps.area))
    has_air_gap = air_gap_area > float(tolerance)

    diagnostics.update(
        {
            "has_air_gap": 1.0 if has_air_gap else 0.0,
            "air_gap_area": air_gap_area,
            "boundary_area": float(max(0.0, boundary_shape.area)),
            "union_area": float(max(0.0, union_shape.area)),
            "geometry_valid": 1.0,
        }
    )

    violations: List[str] = []
    if has_air_gap:
        violations.append(f"Enclosed air gap detected (area={air_gap_area:.4f})")

    return violations, diagnostics


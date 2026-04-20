from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from shapely.geometry import MultiPolygon, Polygon, box
from shapely.ops import unary_union


def validate_empty_space(
    solution: Sequence[Dict[str, Any]],
    floor_width: float,
    floor_height: float,
    wall_union: Dict[str, Any] | None = None,
    tolerance: float = 1e-6,
) -> Tuple[List[str], Dict[str, Any]]:
    """Validate that there are no enclosed air-gaps in room coverage."""
    _ = wall_union
    diagnostics: Dict[str, Any] = {
        "has_air_gap": 0.0,
        "air_gap_area": 0.0,
        "boundary_area": 0.0,
        "union_area": 0.0,
        "floor_area": float(max(1.0, floor_width * floor_height)),
        "tolerance": float(tolerance),
        "geometry_valid": 0.0,
    }

    if not solution:
        diagnostics["geometry_valid"] = 0.0
        return ["Empty solution triggers empty-space validation failure"], diagnostics

    room_polygons = [
        box(
            float(room["x"]),
            float(room["y"]),
            float(room["x_end"]),
            float(room["y_end"]),
        )
        for room in solution
    ]
    union_shape = unary_union(room_polygons)

    if union_shape.is_empty:
        diagnostics["geometry_valid"] = 0.0
        return ["Union of rooms is empty in empty-space validation"], diagnostics

    if isinstance(union_shape, Polygon):
        boundary_shape = Polygon(union_shape.exterior)
    elif isinstance(union_shape, MultiPolygon):
        boundary_shape = MultiPolygon([Polygon(poly.exterior) for poly in union_shape.geoms])
    else:
        polygons = [geom for geom in getattr(union_shape, "geoms", []) if isinstance(geom, Polygon)]
        if not polygons:
            diagnostics["geometry_valid"] = 0.0
            return ["Unsupported union geometry in empty-space validation"], diagnostics
        boundary_shape = MultiPolygon([Polygon(poly.exterior) for poly in polygons])

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

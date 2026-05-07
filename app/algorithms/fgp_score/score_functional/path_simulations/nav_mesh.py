"""Navigation mesh construction.

Builds a Shapely walkable polygon from:
  - Union of all room polygons (total floor area)
  - Thin wall strips along shared room boundaries (re-introduced as obstacles)
  - Door openings punched through those wall strips

No imports from outside this package.
"""

from __future__ import annotations

from typing import Any, List, Tuple

from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import unary_union
from shapely.prepared import prep

# Geometry constants (all in cm)
WALL_THICKNESS: float = 15.0  # thin wall strip half-buffered on shared boundary
DOOR_CUT_RADIUS: float = 11.0  # buffer around door LineString (>WALL_THICKNESS/2)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _to_poly(room: Any) -> Polygon | None:
    verts = getattr(room, "vertices", None)
    if not verts or len(verts) < 3:
        return None
    p = Polygon(verts)
    return p if p.is_valid and not p.is_empty else None


def _iter_polys(geom: Any) -> List[Polygon]:
    if geom is None or getattr(geom, "is_empty", True):
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    return [g for g in getattr(geom, "geoms", []) if isinstance(g, Polygon)]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_nav_mesh(
    rooms: List[Any],
    openings: List[Any],
) -> Tuple[Any, Any]:
    """Return (nav_mesh, total_floor) as Shapely geometries.

    nav_mesh  – walkable area: rooms minus wall strips, with door holes.
    total_floor – raw union of all room polygons (used for bounds / drawing).
    """
    # 1. Room polygons
    room_pairs: List[Tuple[Any, Polygon]] = []
    for r in rooms:
        p = _to_poly(r)
        if p is not None:
            room_pairs.append((r, p))

    if not room_pairs:
        empty = Polygon()
        return empty, empty

    all_polys = [p for _, p in room_pairs]
    total_floor: Any = unary_union(all_polys)

    # 2. Shared wall strips between every adjacent room pair
    wall_strips: List[Any] = []
    n = len(room_pairs)
    for i in range(n):
        for j in range(i + 1, n):
            _, p_i = room_pairs[i]
            _, p_j = room_pairs[j]
            shared = p_i.boundary.intersection(p_j.boundary)
            if shared.is_empty:
                continue
            # Buffer the shared LineString to create a thin wall obstacle
            strip = shared.buffer(
                WALL_THICKNESS / 2.0,
                cap_style="flat",  # Used to be 2
                join_style="mitre",  # Used to be 2
            )
            if not strip.is_empty:
                wall_strips.append(strip)

    # 3. Door hole polygons – buffer each door segment to cut through walls
    door_holes: List[Any] = []
    for op in openings:
        if getattr(op, "opening_type", "") != "door":
            continue
        x1 = float(getattr(op, "x1", 0.0))
        y1 = float(getattr(op, "y1", 0.0))
        x2 = float(getattr(op, "x2", 0.0))
        y2 = float(getattr(op, "y2", 0.0))
        if (x1, y1) == (x2, y2):
            continue
        line = LineString([(x1, y1), (x2, y2)])
        hole = line.buffer(DOOR_CUT_RADIUS, cap_style="flat")  # Used to be 2
        if not hole.is_empty:
            door_holes.append(hole)

    # 4. Assemble nav mesh
    if not wall_strips:
        # No shared walls detected → full floor is walkable
        return total_floor, total_floor

    wall_union: Any = unary_union(wall_strips)
    if door_holes:
        door_union: Any = unary_union(door_holes)
        effective_walls = wall_union.difference(door_union)
    else:
        effective_walls = wall_union

    nav_mesh = total_floor.difference(effective_walls)
    if nav_mesh.is_empty:
        # Fallback: return full floor (better than nothing)
        nav_mesh = total_floor

    return nav_mesh, total_floor

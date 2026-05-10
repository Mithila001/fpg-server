"""Navigation mesh construction.

Builds a Shapely walkable polygon from:
  - Union of all room polygons (total floor area)
  - Thin wall strips along shared room boundaries (re-introduced as obstacles)
  - Door openings punched through those wall strips

No imports from outside this package.
"""

from __future__ import annotations

from typing import Any, List, Tuple

from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import unary_union

from ._dev_print import dev_print

# Geometry constants (all in cm)
WALL_THICKNESS: float = 5.0  # default thin wall strip half-buffered on shared boundary
HALLWAY_WALL_THICKNESS: float = 5.0  # slimmer wall strip so corridors stay usable
DOOR_CUT_RADIUS: float = 11.0  # buffer around door LineString (>WALL_THICKNESS/2)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _is_door_opening(opening: Any) -> bool:
    opening_type = str(_get(opening, "opening_type", "")).lower()
    return "door" in opening_type


def _room_type(room: Any) -> str:
    return str(_get(room, "type", "")).strip().lower()


def _shared_wall_thickness(room_a: Any, room_b: Any) -> float:
    """Use thinner strips when hallways participate in the shared wall."""
    if "hallway" in {_room_type(room_a), _room_type(room_b)}:
        return HALLWAY_WALL_THICKNESS
    return WALL_THICKNESS


def _to_poly(room: Any) -> Polygon | None:
    verts = _get(room, "vertices", None)
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
    dev_print(
        "path", f"Building nav mesh: {len(rooms)} rooms, {len(openings)} openings."
    )

    # 1. Room polygons
    room_pairs: List[Tuple[Any, Polygon]] = []
    for r in rooms:
        p = _to_poly(r)
        if p is not None:
            room_pairs.append((r, p))

    if not room_pairs:
        dev_print("path", "No valid room polygons found. Returning empty mesh.")
        empty = Polygon()
        return empty, empty

    all_polys = [p for _, p in room_pairs]
    total_floor: Any = unary_union(all_polys)
    dev_print("path", f"Total floor area: {total_floor.area:.2f}")

    # 2. Shared wall strips between every adjacent room pair
    wall_strips: List[Any] = []
    n = len(room_pairs)
    for i in range(n):
        for j in range(i + 1, n):
            room_i, p_i = room_pairs[i]
            room_j, p_j = room_pairs[j]
            shared = p_i.boundary.intersection(p_j.boundary)

            if shared.is_empty:
                continue

            # Buffer the shared LineString to create a thin wall obstacle
            wall_thickness = _shared_wall_thickness(room_i, room_j)
            strip = shared.buffer(
                wall_thickness / 2.0,
                cap_style="flat",
                join_style="mitre",
            )
            if not strip.is_empty:
                wall_strips.append(strip)

    dev_print("path", f"Generated {len(wall_strips)} shared wall strips.")

    # 3. Door hole polygons – buffer each door segment to cut through walls
    door_holes: List[Any] = []
    for op in openings:
        if not _is_door_opening(op):
            continue

        x1 = float(_get(op, "x1", 0.0))
        y1 = float(_get(op, "y1", 0.0))
        x2 = float(_get(op, "x2", 0.0))
        y2 = float(_get(op, "y2", 0.0))

        if (x1, y1) == (x2, y2):
            continue

        line = LineString([(x1, y1), (x2, y2)])
        hole = line.buffer(DOOR_CUT_RADIUS, cap_style="flat")
        if not hole.is_empty:
            door_holes.append(hole)

    dev_print("path", f"Generated {len(door_holes)} door hole cutouts.")

    # 4. Assemble nav mesh
    if not wall_strips:
        dev_print("path", "No wall strips found; mesh is equal to total floor.")
        return total_floor, total_floor

    wall_union: Any = unary_union(wall_strips)
    if door_holes:
        door_union: Any = unary_union(door_holes)
        effective_walls = wall_union.difference(door_union)
        dev_print("path", "Doors subtracted from wall strips.")
    else:
        effective_walls = wall_union
        dev_print("path", "No doors to subtract from walls.")

    nav_mesh = total_floor.difference(effective_walls)

    if nav_mesh.is_empty:
        dev_print(
            "path",
            "Warning: Nav mesh is empty after wall subtraction! Falling back to total floor.",
        )
        nav_mesh = total_floor
    else:
        reduction = (1 - (nav_mesh.area / total_floor.area)) * 100
        dev_print(
            "path",
            f"Nav mesh built. Walkable area reduced by {reduction:.2f}% due to walls.",
        )

    return nav_mesh, total_floor

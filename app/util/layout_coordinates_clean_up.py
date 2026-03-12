"""layout_coordinates_clean_up.py

Post-process the raw room-polygon output of ``run_fpg()`` into a clean wall
layout suitable for front-end rendering.

The solver places rooms on a grid so that adjacent rooms can share an edge with
numerically identical (or nearly identical) coordinates.  Naively forwarding all
room polygons to the front end results in duplicate edges being drawn on top of
each other.  This module collapses those duplicates into a single wall segment
per shared boundary and returns:

* A list of unique wall segments, each represented as a pair of (x, y) points.
  The front-end walks these pairs to draw every wall exactly once.
* A list of room descriptors (name, type, centre-point) so the front-end can
  place room labels at the correct position.

Usage::

    polygons, generator = run_fpg(rooms_data=rooms)
    walls, rooms = clean_layout(polygons, generator)

The ``generator`` argument is optional but highly recommended: it gives access to
the room names and types that the solver recorded.  Without it, rooms are
labelled generically as ``"room_0"``, ``"room_1"``, etc.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from app.algorithms.floor_plan_generator import FloorPlanGenerator

# ---------------------------------------------------------------------------
# Public type aliases
# ---------------------------------------------------------------------------

Point = Tuple[float, float]
Segment = Tuple[Point, Point]
RoomInfo = Dict[str, Any]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _euclidean(a: Point, b: Point) -> float:
    """Return the Euclidean distance between two points."""
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def _snap_point(
    pt: Point,
    canonical: List[Point],
    tolerance: float,
) -> Point:
    """Return the existing canonical point closest to ``pt`` if within
    ``tolerance``; otherwise append ``pt`` to ``canonical`` and return it.

    This is O(n) per call but the number of unique vertices in a floor plan is
    small (typically < 100) so the simpler implementation is preferred over a
    spatial index.
    """
    for existing in canonical:
        if _euclidean(pt, existing) <= tolerance:
            return existing
    canonical.append(pt)
    return pt


def _segment_key(a: Point, b: Point) -> Tuple[Point, Point]:
    """Return a canonical, direction-agnostic key for an edge (a, b).

    Sorting the two endpoints ensures that the edge  A→B  and the edge  B→A
    map to the same key so that shared walls between adjacent rooms are treated
    as identical.
    """
    return (min(a, b), max(a, b))


def _polygon_centroid(polygon: List[Point]) -> Point:
    """Return the arithmetic centroid of a convex polygon."""
    n = len(polygon)
    cx = sum(p[0] for p in polygon) / n
    cy = sum(p[1] for p in polygon) / n
    return (cx, cy)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def clean_layout(
    polygons: List[List[Point]],
    generator: Optional["FloorPlanGenerator"] = None,
    tolerance: float = 1e-6,
) -> Tuple[List[Segment], List[RoomInfo]]:
    """Collapse duplicate/overlapping edges and compute room metadata.

    Given the raw polygon list produced by :func:`run_fpg`, this function:

    1. Snaps all vertices that are within ``tolerance`` of each other to a
       single canonical coordinate.  This eliminates floating-point jitter that
       can make two nominally identical points compare unequal.
    2. Extracts every polygon edge and stores it by a direction-agnostic key.
       An edge that appears in two adjacent room polygons is therefore recorded
       only once, representing the single shared wall between those rooms.
    3. Computes the centre point of every room – either from the solver's
       recorded dimensions (``x + w/2``, ``y + h/2``) if a ``generator`` is
       supplied, or from the arithmetic centroid of the polygon otherwise.
    4. Returns the deduplicated wall segments and per-room info list.

    Args:
        polygons:
            List of room polygons as returned by ``run_fpg()``.  Each polygon
            is an ordered list of (x, y) vertices in counter-clockwise order:
            ``[(x, y), (x+w, y), (x+w, y+h), (x, y+h)]``.
        generator:
            Optional :class:`~app.algorithms.floor_plan_generator.FloorPlanGenerator`
            instance used to retrieve room names, types, and exact solver values.
            When provided, ``get_solution()`` is called to obtain per-room
            metadata and precise centre coordinates.
        tolerance:
            Maximum Euclidean distance at which two vertex coordinates are
            considered identical and should be merged.  Defaults to ``1e-6``
            which handles typical floating-point rounding without accidentally
            merging points that are genuinely distinct.

    Returns:
        A two-element tuple ``(walls, rooms)`` where:

        **walls** – ``List[Tuple[Point, Point]]``
            Each entry is a pair of (x, y) points that define one wall segment.
            Walls shared between two rooms appear exactly once.

        **rooms** – ``List[Dict[str, Any]]``
            One entry per room, each a dict with keys:

            * ``"name"``   – room identifier string.
            * ``"type"``   – room type string (e.g. ``"bedroom"``).  Present
              only when ``generator`` is supplied; otherwise an empty string.
            * ``"center"`` – ``(cx, cy)`` float tuple representing the centre
              of the room, suitable for placing a label.

    Example::

        polygons, generator = run_fpg()
        walls, rooms = clean_layout(polygons, generator)

        # walls  → [((0,0),(10,0)), ((10,0),(10,10)), ...]
        # rooms  → [{"name": "bedroom1", "type": "bedroom", "center": (5.0, 5.0)}, ...]
    """
    if not polygons:
        return [], []

    # ------------------------------------------------------------------
    # Step 1: collect room-level metadata from the solver when available
    # ------------------------------------------------------------------
    solver_rooms: List[Dict[str, Any]] = []
    if generator is not None:
        try:
            solver_rooms = generator.get_solution()
        except Exception:
            # If the generator has no solution yet (e.g. solve not called),
            # fall back to polygon-based centre computation.
            solver_rooms = []

    # Pad with empty dicts so we can always do solver_rooms[i] safely
    while len(solver_rooms) < len(polygons):
        solver_rooms.append({})

    # ------------------------------------------------------------------
    # Step 2: snap vertices to canonical points and extract unique edges
    # ------------------------------------------------------------------
    canonical_pts: List[Point] = []
    # Use a set of direction-agnostic edge keys for deduplication.
    seen_keys: set = set()
    unique_walls: List[Segment] = []

    for polygon in polygons:
        if not polygon:
            continue

        snapped = [_snap_point(pt, canonical_pts, tolerance) for pt in polygon]

        n = len(snapped)
        for i in range(n):
            a = snapped[i]
            b = snapped[(i + 1) % n]
            key = _segment_key(a, b)
            if key not in seen_keys:
                seen_keys.add(key)
                unique_walls.append((a, b))

    # ------------------------------------------------------------------
    # Step 3: build per-room info with centre coordinates
    # ------------------------------------------------------------------
    room_list: List[RoomInfo] = []
    for idx, polygon in enumerate(polygons):
        sr = solver_rooms[idx]

        name: str = sr.get("name") or f"room_{idx}"
        room_type: str = sr.get("type", "")

        # Prefer solver-recorded dimensions for a precise centre
        if sr.get("x") is not None and sr.get("w") is not None:
            cx = float(sr["x"]) + float(sr["w"]) / 2.0
            cy = float(sr["y"]) + float(sr["h"]) / 2.0
            center: Point = (cx, cy)
        else:
            center = _polygon_centroid(polygon)

        room_list.append(
            {
                "name": name,
                "type": room_type,
                "center": center,
            }
        )

    return unique_walls, room_list


def validate_layout(
    polygons: List[List[Point]],
    generator: Optional["FloorPlanGenerator"] = None,
    tolerance: float = 1e-6,
) -> Dict[str, Any]:
    """Produce diagnostics comparing raw and cleaned floor-plan data.

    This helper is intended for development use when the front-end drawings look
    incorrect.  It runs ``clean_layout`` internally and also computes a mapping
    of every edge present in the raw polygon data to the set of rooms that
    reference it.  The returned report can help verify that shared walls are
    being merged correctly and that no edges were lost.

    The returned dictionary contains:

    * ``raw_edge_count`` – total number of polygon edges before any processing.
    * ``canonical_edge_count`` – number of distinct edges after snapping points
      but before deduplication.
    * ``clean_edge_count`` – number of edges returned by ``clean_layout``.
    * ``merged_count`` – number of edges that were shared by more than one room.
    * ``merged_edges`` – list of objects ``{"edge": (p1, p2), "rooms": [idx,...]}``
      showing which cleaned edges originate from multiple rooms.
    * ``walls`` and ``rooms`` – the normal output of ``clean_layout`` for easy
      reference in the same payload.
    """
    # run normal cleaning so we have the standard result to return as part of
    # the report
    walls, rooms = clean_layout(polygons, generator, tolerance)

    # build canonical-edge map from the raw polygons
    canonical_pts: List[Point] = []
    edges_map: Dict[Tuple[Point, Point], List[int]] = {}

    for rid, poly in enumerate(polygons):
        snapped = [_snap_point(pt, canonical_pts, tolerance) for pt in poly]
        n = len(snapped)
        for i in range(n):
            key = _segment_key(snapped[i], snapped[(i + 1) % n])
            edges_map.setdefault(key, []).append(rid)

    merged = [
        {"edge": edge, "rooms": rooms_list}
        for edge, rooms_list in edges_map.items()
        if len(rooms_list) > 1
    ]

    # detect colinear overlapping edges that were not merged
    def _colinear(p: Point, q: Point, r: Point) -> bool:
        # area of triangle pqr is zero if colinear
        return abs((q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])) <= tolerance

    def _proj_interval(a: Point, b: Point) -> Tuple[float, float]:
        # project a and b onto their dominant axis (x or y) depending on orientation
        if abs(a[0] - b[0]) <= tolerance:
            # vertical line, compare y-values
            return (min(a[1], b[1]), max(a[1], b[1]))
        else:
            # horizontal or slanted; project on x
            return (min(a[0], b[0]), max(a[0], b[0]))

    overlaps = []
    edge_list = list(edges_map.keys())
    for i in range(len(edge_list)):
        a1, a2 = edge_list[i]
        for j in range(i + 1, len(edge_list)):
            b1, b2 = edge_list[j]
            # skip identical segments (they would appear in merged_edges)
            if _segment_key(a1, a2) == _segment_key(b1, b2):
                continue
            # check if colinear
            if (_colinear(a1, a2, b1) and _colinear(a1, a2, b2)):
                # check projection overlap
                ia1, ia2 = _proj_interval(a1, a2)
                ib1, ib2 = _proj_interval(b1, b2)
                if ia2 + tolerance >= ib1 and ib2 + tolerance >= ia1:
                    # overlapping intervals
                    overlaps.append({
                        "segment_a": (a1, a2),
                        "segment_b": (b1, b2),
                        "rooms_a": edges_map[(a1, a2)],
                        "rooms_b": edges_map[(b1, b2)],
                    })

    return {
        "raw_edge_count": sum(len(poly) for poly in polygons),
        "canonical_edge_count": len(edges_map),
        "clean_edge_count": len(walls),
        "merged_count": len(merged),
        "merged_edges": merged,
        "overlaps": overlaps,
        "walls": walls,
        "rooms": rooms,
    }

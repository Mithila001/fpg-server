"""Extract named simulation anchor points from rooms + openings.

Entry door strategy: find the door shared between livingRoom and
verandaOutdoorSpace – that midpoint is the "front door".
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

# Internal Import
from ._dev_print import dev_print

_WorldPt = Tuple[float, float]
BATHROOM_TYPES = {"bathroom", "attachedBathroom"}


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _is_door_opening(opening: Any) -> bool:
    opening_type = str(_get(opening, "opening_type", "")).lower()
    return "door" in opening_type


def _door_midpoint(opening: Any) -> _WorldPt:
    x1 = float(_get(opening, "x1", 0.0))
    y1 = float(_get(opening, "y1", 0.0))
    x2 = float(_get(opening, "x2", 0.0))
    y2 = float(_get(opening, "y2", 0.0))
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def _room_centroid(room: Any) -> _WorldPt:
    verts: List[_WorldPt] = _get(room, "vertices", [])
    if not verts:
        return (0.0, 0.0)
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def _distance(a: _WorldPt, b: _WorldPt) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def _doors_only(openings: List[Any]) -> List[Any]:
    return [op for op in openings if _is_door_opening(op)]


def _connecting_types(op: Any) -> tuple[str, str]:
    return (
        str(_get(op, "room_type", "")),
        str(_get(op, "connected_room_type", "")),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_simulation_points(
    rooms: List[Any], openings: List[Any]
) -> Dict[str, _WorldPt]:
    dev_print(
        "path_status",
        f"Extracting points for {len(rooms)} rooms and {len(openings)} openings.",
    )

    doors = _doors_only(openings)
    points: Dict[str, _WorldPt] = {}

    # --- Front door ---
    for op in doors:
        rt, crt = _connecting_types(op)
        if "livingRoom" in {rt, crt} and "verandaOutdoorSpace" in {rt, crt}:
            points["front_door"] = _door_midpoint(op)
            dev_print("path_front_door", f"Located at {points['front_door']}")
            break

    # --- Kitchen ---
    kitchen_rooms = [r for r in rooms if _get(r, "type", "") == "kitchen"]
    if kitchen_rooms:
        kr = kitchen_rooms[0]
        kitchen_door = next(
            (op for op in doors if "kitchen" in _connecting_types(op)), None
        )

        if kitchen_door:
            points["kitchen"] = _door_midpoint(kitchen_door)
            dev_print("path_kitchen", f"Anchor set via door: {points['kitchen']}")
        else:
            points["kitchen"] = _room_centroid(kr)
            dev_print(
                "path_kitchen", f"Anchor set via fallback centroid: {points['kitchen']}"
            )

    # --- Room Door Lookup ---
    door_by_room: Dict[str, List[Any]] = {}
    for op in doors:
        rn = str(_get(op, "room_name", ""))
        crn = str(_get(op, "connected_room_name", ""))
        door_by_room.setdefault(rn, []).append(op)
        door_by_room.setdefault(crn, []).append(op)

    # --- Bedrooms ---
    bedrooms = [r for r in rooms if _get(r, "type", "") == "bedroom"]
    for idx, room in enumerate(bedrooms):
        rname = str(_get(room, "name", ""))
        room_doors = door_by_room.get(rname, [])
        pt = _door_midpoint(room_doors[0]) if room_doors else _room_centroid(room)
        points[f"bedroom_{idx}"] = pt
        dev_print("path_bedroom", f"bedroom_{idx} ({rname}) -> {pt}")

    # --- Bathrooms ---
    bathrooms = [r for r in rooms if _get(r, "type", "") in BATHROOM_TYPES]
    for idx, room in enumerate(bathrooms):
        rname = str(_get(room, "name", ""))
        room_doors = door_by_room.get(rname, [])
        pt = _door_midpoint(room_doors[0]) if room_doors else _room_centroid(room)
        points[f"bathroom_{idx}"] = pt
        dev_print("path_bathroom", f"bathroom_{idx} ({rname}) -> {pt}")

    dev_print("path_complete", f"Total anchors mapped: {list(points.keys())}")
    return points


def nearest_bathroom_key(
    bedroom_key: str, points: Dict[str, _WorldPt]
) -> Optional[str]:
    if bedroom_key not in points:
        dev_print("path_error", f"Key {bedroom_key} missing from points.")
        return None

    bed_pt = points[bedroom_key]
    best_key, best_dist = None, float("inf")

    for key, pt in points.items():
        if key.startswith("bathroom_"):
            d = _distance(bed_pt, pt)
            if d < best_dist:
                best_dist, best_key = d, key

    dev_print("path_nearest", f"{bedroom_key} -> {best_key} (dist: {best_dist:.2f})")
    return best_key

from typing import Iterable
import math

from .geom import centroid_from_vertices, polygon_shared_edge


def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _find_room_by_types(rooms: Iterable[object], type_names: set[str]):
    for r in rooms or []:
        t = str(_get(r, "type", "")).lower()
        if t in type_names:
            return r
    return None


def score_kitchen_dining(
    rooms: Iterable[object], max_distance: float = 2000.0
) -> float:
    """Score kitchen-dining adjacency: 100 if shared wall, otherwise distance-based.

    Types accepted for dining room include common variants.
    """
    if not rooms:
        return 0.0

    dining_types = {"dining", "diningroom", "dining_room", "diningroom", "diningroom"}
    kitchen_types = {"kitchen"}

    kitchen = _find_room_by_types(rooms, kitchen_types)
    dining = _find_room_by_types(rooms, dining_types)

    # If either missing, return neutral good score
    if kitchen is None or dining is None:
        return 100.0

    # Shared wall -> perfect
    try:
        if polygon_shared_edge(kitchen, dining):
            return 100.0
    except Exception:
        pass

    # Fallback to centroid distance
    kv = (
        getattr(kitchen, "vertices", None)
        if not isinstance(kitchen, dict)
        else kitchen.get("vertices")
    )
    dv = (
        getattr(dining, "vertices", None)
        if not isinstance(dining, dict)
        else dining.get("vertices")
    )
    kv = kv or []
    dv = dv or []
    kc = centroid_from_vertices(kv)
    dc = centroid_from_vertices(dv)
    dx = kc[0] - dc[0]
    dy = kc[1] - dc[1]
    d = math.hypot(dx, dy)
    frac = min(1.0, d / max_distance)
    score = max(0.0, 100.0 - frac * 100.0)
    return score

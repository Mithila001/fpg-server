from typing import Iterable


def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def score_living_room(rooms: Iterable[object]) -> float:
    """Score living room balance. Higher score is better (0-100).

    If living room area is <= sum(other areas) => return 100. Otherwise penalize
    based on how much larger the living room is.
    """
    rs = list(rooms or [])
    if not rs:
        return 0.0

    living = None
    for r in rs:
        if (
            str(_get(r, "type", "")).lower() == "livingroom"
            or str(_get(r, "type", "")).lower() == "living_room"
        ):
            living = r
            break

    if living is None:
        return 100.0

    living_area = float(_get(living, "area", 0.0) or 0.0)
    other_area = 0.0
    for r in rs:
        if r is living:
            continue
        other_area += float(_get(r, "area", 0.0) or 0.0)

    # If living room is not larger than rest combined, it's ideal
    if living_area <= other_area or other_area <= 0.0:
        return 100.0

    # Ratio >1 means living is larger. Map ratio to penalty.
    ratio = living_area / max(other_area, 1e-6)
    # scale controls how quickly score drops; scale=2.0 -> ratio 3 yields zero.
    scale = 2.0
    penalty_frac = min(1.0, (ratio - 1.0) / scale)
    score = max(0.0, 100.0 - penalty_frac * 100.0)
    return score

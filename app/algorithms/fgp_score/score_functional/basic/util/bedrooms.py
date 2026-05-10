from typing import Iterable
import math


def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def score_bedrooms(rooms: Iterable[object], min_bed_area: float = 900.0) -> float:
    """Return bedroom sizing/consistency score (0-100).

    - Heavy penalty if any bedroom area < min_bed_area.
    - Penalize spread between bedrooms (max-min relative to mean).
    """
    rs = [r for r in (rooms or []) if str(_get(r, "type", "")).lower() == "bedroom"]
    if not rs:
        return 100.0

    areas = [float(_get(r, "area", 0.0) or 0.0) for r in rs]
    if not areas:
        return 100.0

    heavy_penalty = 0.0
    if any(a < min_bed_area for a in areas):
        heavy_penalty = 60.0  # heavy non-zero penalty

    if len(areas) == 1:
        spread_penalty = 0.0
    else:
        mx = max(areas)
        mn = min(areas)
        mean = sum(areas) / len(areas) if areas else 1.0
        rel_spread = (mx - mn) / max(mean, 1e-6)
        # Map relative spread to up to 40 points penalty. Assume rel_spread 0.5 -> full 40
        spread_penalty = min(40.0, (rel_spread / 0.5) * 40.0)

    raw = max(0.0, 100.0 - heavy_penalty - spread_penalty)
    return raw

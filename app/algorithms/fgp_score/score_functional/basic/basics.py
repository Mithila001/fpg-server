from app.algorithms.types.openings import FloorPlanWithOpenings

from .util import (
    score_living_room,
    score_bedrooms,
    score_kitchen_dining,
)


def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def score_basic_functional(
    floor_plan: FloorPlanWithOpenings, score_margin: float
) -> float:
    """Aggregate basic functional scores and normalize to `score_margin`.

    Combines three equal-weighted sub-scores:
    - living room balance
    - bedroom sizing/consistency
    - kitchen-dining adjacency

    Returns a float in range 0..score_margin.
    """
    rooms = _get(floor_plan, "floor_plan", [])

    if not rooms:
        return 0.0

    s1 = float(score_living_room(rooms) or 0.0)
    s2 = float(score_bedrooms(rooms) or 0.0)
    s3 = float(score_kitchen_dining(rooms) or 0.0)

    # Equal weights
    raw = (s1 + s2 + s3) / 3.0

    final_score = (raw / 100.0) * float(score_margin)
    return final_score

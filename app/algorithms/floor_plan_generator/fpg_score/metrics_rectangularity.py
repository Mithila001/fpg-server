from __future__ import annotations

from typing import Any, Dict, Sequence, Tuple


def score_rectangularity(solution: Sequence[Dict[str, Any]]) -> Tuple[float, Dict[str, float]]:
    """Rectangularity score in [0, 100] based on area / bounding-box-area."""
    used_area = sum(int(room["area"]) for room in solution)

    min_x = min(int(room["x"]) for room in solution)
    min_y = min(int(room["y"]) for room in solution)
    max_x = max(int(room["x_end"]) for room in solution)
    max_y = max(int(room["y_end"]) for room in solution)

    bbox_area = max(1, (max_x - min_x) * (max_y - min_y))
    ratio = max(0.0, min(1.0, used_area / bbox_area))
    score = ratio * 100.0

    return score, {
        "used_area": float(used_area),
        "bbox_area": float(bbox_area),
        "rectangularity_ratio": ratio,
    }

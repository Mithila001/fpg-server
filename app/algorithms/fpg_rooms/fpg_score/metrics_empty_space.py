from __future__ import annotations

from typing import Any, Dict, Sequence, Tuple


def score_empty_space(
    solution: Sequence[Dict[str, Any]],
    floor_width: float,
    floor_height: float,
) -> Tuple[float, Dict[str, float]]:
    """Empty-space score in [0, 100] using floor and envelope void ratios."""
    floor_area = max(1, int(floor_width) * int(floor_height))
    used_area = sum(int(room["area"]) for room in solution)

    floor_void_ratio = max(0.0, (floor_area - used_area) / floor_area)

    min_x = min(int(room["x"]) for room in solution)
    min_y = min(int(room["y"]) for room in solution)
    max_x = max(int(room["x_end"]) for room in solution)
    max_y = max(int(room["y_end"]) for room in solution)

    bbox_area = max(1, (max_x - min_x) * (max_y - min_y))
    bbox_void_ratio = max(0.0, (bbox_area - used_area) / bbox_area)

    # Blend global floor emptiness and local packing quality.
    blended_void = 0.6 * floor_void_ratio + 0.4 * bbox_void_ratio
    score = max(0.0, min(100.0, 100.0 * (1.0 - blended_void)))

    return score, {
        "floor_void_ratio": floor_void_ratio,
        "bbox_void_ratio": bbox_void_ratio,
        "bbox_area": float(bbox_area),
        "blended_void": blended_void,
    }

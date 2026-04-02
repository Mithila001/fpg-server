from __future__ import annotations

from typing import Any, Dict, Sequence, Tuple


def score_coverage(
    solution: Sequence[Dict[str, Any]],
    floor_width: float,
    floor_height: float,
    min_coverage: float,
) -> Tuple[float, Dict[str, float]]:
    """Coverage score in [0, 100], with strong penalty below threshold."""
    floor_area = max(1, int(floor_width) * int(floor_height))
    used_area = sum(int(room["area"]) for room in solution)
    coverage_ratio = used_area / floor_area

    threshold = max(1e-9, float(min_coverage))
    if coverage_ratio >= threshold:
        score = 100.0
    else:
        score = max(0.0, 100.0 * (coverage_ratio / threshold))

    return score, {
        "floor_area": float(floor_area),
        "used_area": float(used_area),
        "coverage_ratio": coverage_ratio,
        "min_coverage": float(min_coverage),
    }
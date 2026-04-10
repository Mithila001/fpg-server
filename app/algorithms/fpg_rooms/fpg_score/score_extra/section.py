from __future__ import annotations

from typing import Any, Dict, Sequence, Tuple


def _layout_has_types(solution: Sequence[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
    type_count = sum(1 for room in solution if str(room.get("type", "")).strip())
    return type_count == len(solution), {"typed_rooms": type_count, "room_count": len(solution)}


def _layout_has_bounds(solution: Sequence[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
    has_invalid_bounds = any(
        float(room.get("x_end", 0.0)) <= float(room.get("x", 0.0))
        or float(room.get("y_end", 0.0)) <= float(room.get("y", 0.0))
        for room in solution
    )
    return not has_invalid_bounds, {"has_invalid_bounds": has_invalid_bounds}


def _layout_has_area(solution: Sequence[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
    total_area = sum(float(room.get("area", 0.0)) for room in solution)
    return total_area > 0.0, {"total_area": total_area}


def score_extra_section(solution: Sequence[Dict[str, Any]]) -> Tuple[float, Dict[str, Any]]:
    """Score extra section in [0, 25] using executable placeholder checks."""
    checks = [
        ("typed_rooms", _layout_has_types),
        ("valid_bounds", _layout_has_bounds),
        ("positive_total_area", _layout_has_area),
    ]

    check_results = []
    passed_count = 0
    for check_name, check_fn in checks:
        passed, check_diag = check_fn(solution)
        if passed:
            passed_count += 1
        check_results.append(
            {
                "name": check_name,
                "passed": passed,
                "diagnostics": check_diag,
            }
        )

    score = 25.0 * (passed_count / len(checks)) if checks else 0.0
    diagnostics = {
        "executed_checks": len(checks),
        "passed_checks": passed_count,
        "checks": check_results,
    }
    return max(0.0, min(25.0, score)), diagnostics

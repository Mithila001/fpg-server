from __future__ import annotations

from typing import Any, Dict, Sequence, Tuple


def _has_rooms(solution: Sequence[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
    count = len(solution)
    return count > 0, {"room_count": count}


def _all_rooms_have_positive_area(solution: Sequence[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
    areas = [float(room.get("area", 0.0)) for room in solution]
    min_area = min(areas) if areas else 0.0
    return all(area > 0.0 for area in areas), {"min_area": min_area}


def _room_names_present(solution: Sequence[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
    missing_name_count = sum(1 for room in solution if not str(room.get("name", "")).strip())
    return missing_name_count == 0, {"missing_name_count": missing_name_count}


def score_functional_section(solution: Sequence[Dict[str, Any]]) -> Tuple[float, Dict[str, Any]]:
    """Score functional section in [0, 25] using executable placeholder checks."""
    checks = [
        ("has_rooms", _has_rooms),
        ("positive_area", _all_rooms_have_positive_area),
        ("room_names_present", _room_names_present),
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

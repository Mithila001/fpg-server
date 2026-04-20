from __future__ import annotations

from typing import Any, Dict, Sequence, Tuple

from .opening import (
    evaluate_back_door_placement,
    evaluate_internal_doors_placement,
    evaluate_main_door_to_outside,
    evaluate_windows_placement,
)


def _clamp_0_25(value: float) -> float:
    return max(0.0, min(25.0, float(value)))


def score_functional_section(
    solution: Sequence[Dict[str, Any]],
    openings: Sequence[Dict[str, Any]] | None = None,
) -> Tuple[float, Dict[str, Any]]:
    """Score functional section in [0, 25] using opening-placement evaluations."""
    opening_data = openings or []

    evaluators = [
        ("main_door_to_outside", evaluate_main_door_to_outside),
        ("internal_doors_placement", evaluate_internal_doors_placement),
        ("back_door_placement", evaluate_back_door_placement),
        ("windows_placement", evaluate_windows_placement),
    ]

    evaluator_results: list[Dict[str, Any]] = []
    evaluator_scores: list[float] = []

    for evaluator_name, evaluator_fn in evaluators:
        evaluator_score, evaluator_diag = evaluator_fn(solution, opening_data)
        evaluator_scores.append(float(evaluator_score))
        evaluator_results.append(
            {
                "name": evaluator_name,
                "score": round(float(evaluator_score), 2),
                "diagnostics": evaluator_diag,
            }
        )

    score = _clamp_0_25(sum(evaluator_scores) / len(evaluator_scores)) if evaluator_scores else 0.0
    diagnostics = {
        "executed_checks": len(evaluators),
        "openings_count": len(opening_data),
        "evaluators": evaluator_results,
    }
    return score, diagnostics

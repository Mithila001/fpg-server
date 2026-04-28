from __future__ import annotations

from typing import Any, Dict, Sequence, Tuple

from .opening import (
    evaluate_back_door_placement,
    evaluate_internal_doors_placement,
    evaluate_main_door_to_outside,
    evaluate_windows_placement,
)
from .path_simulations.path_simulator import evaluate_path_simulation


def _clamp_0_25(value: float) -> float:
    return max(0.0, min(25.0, float(value)))


def _clamp_0_15(value: float) -> float:
    return max(0.0, min(15.0, float(value)))


def score_functional_section(
    solution: Sequence[Dict[str, Any]],
    openings: Sequence[Dict[str, Any]] | None = None,
) -> Tuple[float, Dict[str, Any]]:
    """Score functional section in [0, 25] using openings and path simulation."""
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

    opening_avg = (
        (sum(evaluator_scores) / len(evaluator_scores)) if evaluator_scores else 0.0
    )
    opening_score = _clamp_0_15((opening_avg / 25.0) * 15.0) if evaluator_scores else 0.0

    path_score, path_diag = evaluate_path_simulation(
        solution,
        opening_data,
        enable_dev_plot=True,
    )
    print(f"Path Simulation Score: {path_score}, Diagnostics: {path_diag}")
    total_score = _clamp_0_25(opening_score + float(path_score))
    diagnostics = {
        "executed_checks": len(evaluators) + 1,
        "openings_count": len(opening_data),
        "opening_score_scaled": round(float(opening_score), 2),
        "opening_score_raw_avg": round(float(opening_avg), 2),
        "path_simulation": {
            "score": round(float(path_score), 2),
            "max_score": 10.0,
            "diagnostics": path_diag,
        },
        "evaluators": evaluator_results,
    }
    return total_score, diagnostics

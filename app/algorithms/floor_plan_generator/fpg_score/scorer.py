from __future__ import annotations

from typing import Any, Dict, Sequence

from .metrics_coverage import score_coverage
from .metrics_empty_space import score_empty_space
from .metrics_rectangularity import score_rectangularity
from .types import ScoreReport
from .validators import (
    validate_adjacency_relations,
    validate_no_overlap,
    validate_room_geometry,
)

DEFAULT_WEIGHTS = {
    "coverage": 0.40,
    "rectangularity": 0.35,
    "empty_space": 0.25,
}


def score_layout(
    solution: Sequence[Dict[str, Any]],
    requirements: Any,
    min_touch_overlap: int = 1,
) -> ScoreReport:
    """Score a solved floor-plan layout.

    Hard checks (geometry, overlap, adjacency) are a gate. When a hard check
    fails, total_score becomes 0 while diagnostics are still returned.
    """
    if not solution:
        return ScoreReport(
            valid=False,
            total_score=0.0,
            hard_violations=["Solution is empty"],
            diagnostics={},
        )

    cfg = requirements.config
    floor_width = float(cfg.floor_plan_width)
    floor_height = float(cfg.floor_plan_height)
    min_coverage = float(cfg.min_coverage)

    relation_constraints = getattr(requirements, "relation_constraints", []) or []

    hard_violations = []
    hard_violations.extend(validate_room_geometry(solution, floor_width, floor_height))
    hard_violations.extend(validate_no_overlap(solution))
    hard_violations.extend(
        validate_adjacency_relations(
            solution,
            relation_constraints,
            min_overlap=min_touch_overlap,
        )
    )

    coverage_score, coverage_diag = score_coverage(
        solution,
        floor_width,
        floor_height,
        min_coverage,
    )
    rectangularity_score, rectangularity_diag = score_rectangularity(solution)
    empty_space_score, empty_space_diag = score_empty_space(
        solution,
        floor_width,
        floor_height,
    )

    component_scores = {
        "coverage": coverage_score,
        "rectangularity": rectangularity_score,
        "empty_space": empty_space_score,
    }

    diagnostics = {
        "coverage": coverage_diag,
        "rectangularity": rectangularity_diag,
        "empty_space": empty_space_diag,
        "weights": DEFAULT_WEIGHTS,
    }

    valid = len(hard_violations) == 0
    if not valid:
        return ScoreReport(
            valid=False,
            total_score=0.0,
            component_scores=component_scores,
            hard_violations=hard_violations,
            diagnostics=diagnostics,
        )

    total_score = (
        component_scores["coverage"] * DEFAULT_WEIGHTS["coverage"]
        + component_scores["rectangularity"] * DEFAULT_WEIGHTS["rectangularity"]
        + component_scores["empty_space"] * DEFAULT_WEIGHTS["empty_space"]
    )

    return ScoreReport(
        valid=True,
        total_score=round(total_score, 2),
        component_scores={k: round(v, 2) for k, v in component_scores.items()},
        hard_violations=[],
        diagnostics=diagnostics,
    )

from __future__ import annotations

from typing import Any, Dict, Sequence

from app.core.config_fpg import (
    ENVELOPE_APPLY_SIDES,
    ENVELOPE_ENABLED,
    ENVELOPE_EXCLUDE_TYPES,
    ENVELOPE_MAX_GAP,
    ENVELOPE_MIN_GAP,
    SCORE_WEIGHTS,
)
from .metrics_coverage import score_coverage
from .metrics_empty_space import score_empty_space
from .metrics_rectangularity import score_rectangularity
from .types import ScoreReport
from .validators import (
    validate_adjacency_relations,
    validate_envelope_staircase_bounds,
    validate_no_overlap,
    validate_room_geometry,
)

DEFAULT_WEIGHTS = SCORE_WEIGHTS.copy()


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
    if bool(getattr(cfg, "envelope_enabled", ENVELOPE_ENABLED)):
        hard_violations.extend(
            validate_envelope_staircase_bounds(
                solution,
                min_gap=int(getattr(cfg, "envelope_min_gap", ENVELOPE_MIN_GAP)),
                max_gap=int(getattr(cfg, "envelope_max_gap", ENVELOPE_MAX_GAP)),
                exclude_types=getattr(cfg, "envelope_exclude_types", ENVELOPE_EXCLUDE_TYPES),
                apply_sides=getattr(cfg, "envelope_apply_sides", ENVELOPE_APPLY_SIDES),
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

    weights = getattr(cfg, "score_weights", SCORE_WEIGHTS)
    if weights is None:
        weights = SCORE_WEIGHTS

    diagnostics = {
        "coverage": coverage_diag,
        "rectangularity": rectangularity_diag,
        "empty_space": empty_space_diag,
        "weights": weights,
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
        component_scores["coverage"] * float(weights.get("coverage", SCORE_WEIGHTS["coverage"]))
        + component_scores["rectangularity"] * float(weights.get("rectangularity", SCORE_WEIGHTS["rectangularity"]))
        + component_scores["empty_space"] * float(weights.get("empty_space", SCORE_WEIGHTS["empty_space"]))
    )

    return ScoreReport(
        valid=True,
        total_score=round(total_score, 2),
        component_scores={k: round(v, 2) for k, v in component_scores.items()},
        hard_violations=[],
        diagnostics=diagnostics,
    )

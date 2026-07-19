from __future__ import annotations

import pytest
from typing import cast

from app.algorithms.candidate_scoring import (
    CandidateScoringInput,
    EvaluationStatus,
    EvaluatorKey,
    EvaluatorResult,
    EvaluatorRule,
    EvaluatorCategory,
    ScoringContext,
)
from app.algorithms.types_new import FloorPlanGenerationSpec


def test_evaluator_rule_copies_and_freezes_settings() -> None:
    source = {"grid_size": 3}
    rule = EvaluatorRule(
        key=EvaluatorKey("quality"),
        category=EvaluatorCategory.QUALITY,
        settings=source,
    )
    source["grid_size"] = 99

    assert rule.settings["grid_size"] == 3
    with pytest.raises(TypeError):
        rule.settings["grid_size"] = 4  # type: ignore[index]


def test_scoring_context_copies_and_freezes_derived_values() -> None:
    source = {"prepared": 1}
    context = ScoringContext(
        scoring_input=CandidateScoringInput(
            specification=cast(FloorPlanGenerationSpec, {}),
            candidate={},
        ),
        derived=source,
    )
    source["prepared"] = 2

    assert context.derived["prepared"] == 1
    with pytest.raises(TypeError):
        context.derived["prepared"] = 3  # type: ignore[index]


def test_evaluator_result_copies_and_freezes_metrics() -> None:
    source = {"distance": 4.0}
    result = EvaluatorResult(
        evaluator_key=EvaluatorKey("quality"),
        status=EvaluationStatus.COMPLETED,
        score=80.0,
        metrics=source,
    )
    source["distance"] = 8.0

    assert result.metrics["distance"] == pytest.approx(4.0)
    with pytest.raises(TypeError):
        result.metrics["distance"] = 1.0  # type: ignore[index]

from __future__ import annotations

import math
from typing import cast

import pytest
from app.algorithms.types_new import FloorPlanGenerationSpec

from app.algorithms.candidate_scoring import (
    CandidateScoreManager,
    CandidateScoringInput,
    EvaluationStatus,
    EvaluatorCategory,
    EvaluatorRegistry,
)
from app.algorithms.candidate_scoring.exceptions import (
    EvaluatorContractError,
    ScoringConfigurationError,
    ScoringInputError,
)

from .builders import build_rule, build_scoring_config, build_scoring_input
from .fakes import FakeEvaluator


def test_scoring_input_rejects_missing_specification() -> None:
    evaluator = FakeEvaluator("quality")
    manager = CandidateScoreManager(
        EvaluatorRegistry((evaluator,)),
        build_scoring_config(build_rule("quality")),
    )

    with pytest.raises(ScoringInputError, match="specification"):
        manager.score(
            CandidateScoringInput(
                specification=cast(FloorPlanGenerationSpec, None),
                candidate={},
            )
        )


def test_scoring_input_rejects_missing_candidate() -> None:
    evaluator = FakeEvaluator("quality")
    manager = CandidateScoreManager(
        EvaluatorRegistry((evaluator,)),
        build_scoring_config(build_rule("quality")),
    )

    with pytest.raises(ScoringInputError, match="candidate"):
        manager.score(
            CandidateScoringInput(
                specification=cast(FloorPlanGenerationSpec, {}),
                candidate=None,
            )
        )


def test_config_requires_at_least_one_rule() -> None:
    with pytest.raises(ScoringConfigurationError, match="At least one evaluator rule"):
        CandidateScoreManager(EvaluatorRegistry(), build_scoring_config())


def test_config_rejects_duplicate_rule_keys() -> None:
    evaluator = FakeEvaluator("same")

    with pytest.raises(ScoringConfigurationError, match="configured more than once"):
        CandidateScoreManager(
            EvaluatorRegistry((evaluator,)),
            build_scoring_config(build_rule("same"), build_rule("same")),
        )


def test_config_rejects_enabled_rule_without_registered_evaluator() -> None:
    with pytest.raises(ScoringConfigurationError, match="not registered"):
        CandidateScoreManager(
            EvaluatorRegistry(),
            build_scoring_config(build_rule("missing")),
        )


@pytest.mark.parametrize("weight", [-1.0, math.inf, math.nan])
def test_config_rejects_invalid_weights(weight: float) -> None:
    evaluator = FakeEvaluator("quality")

    with pytest.raises(ScoringConfigurationError, match="invalid weight"):
        CandidateScoreManager(
            EvaluatorRegistry((evaluator,)),
            build_scoring_config(build_rule("quality", weight=weight)),
        )


def test_quality_rule_requires_positive_weight() -> None:
    evaluator = FakeEvaluator("quality")

    with pytest.raises(ScoringConfigurationError, match="positive weight"):
        CandidateScoreManager(
            EvaluatorRegistry((evaluator,)),
            build_scoring_config(build_rule("quality", weight=0.0)),
        )


def test_critical_rule_requires_minimum_score() -> None:
    critical = FakeEvaluator("critical")
    quality = FakeEvaluator("quality")
    critical_rule = build_rule(
        "critical",
        category=EvaluatorCategory.CRITICAL,
        minimum_score=50.0,
    )
    object.__setattr__(critical_rule, "minimum_score", None)

    with pytest.raises(ScoringConfigurationError, match="requires minimum_score"):
        CandidateScoreManager(
            EvaluatorRegistry((critical, quality)),
            build_scoring_config(critical_rule, build_rule("quality")),
        )


@pytest.mark.parametrize(
    ("evaluator", "expected_message"),
    [
        (
            FakeEvaluator("expected", returned_key="other", score=50.0),
            "returned result for",
        ),
        (
            FakeEvaluator("expected", status=EvaluationStatus.COMPLETED, score=None),
            "completed without a score",
        ),
        (
            FakeEvaluator("expected", status=EvaluationStatus.COMPLETED, score=101.0),
            "must be between",
        ),
        (
            FakeEvaluator(
                "expected",
                status=EvaluationStatus.NOT_APPLICABLE,
                score=50.0,
            ),
            "returned a score while status",
        ),
    ],
)
def test_evaluator_contract_violations_can_be_reraised(
    evaluator: FakeEvaluator,
    expected_message: str,
) -> None:
    manager = CandidateScoreManager(
        EvaluatorRegistry((evaluator,)),
        build_scoring_config(
            build_rule("expected"),
            raise_on_evaluator_error=True,
        ),
    )

    with pytest.raises(EvaluatorContractError, match=expected_message):
        manager.score(build_scoring_input())


def test_contract_violation_becomes_error_result_by_default() -> None:
    evaluator = FakeEvaluator("expected", score=-1.0)
    manager = CandidateScoreManager(
        EvaluatorRegistry((evaluator,)),
        build_scoring_config(build_rule("expected")),
    )

    result = manager.score(build_scoring_input())

    execution = result.evaluator_results[0]
    assert execution.status is EvaluationStatus.ERROR
    assert execution.raw_score is None
    assert execution.contribution == 0.0
    assert execution.findings[0].code == "EVALUATOR_ERROR"
    assert result.total_score == 0.0

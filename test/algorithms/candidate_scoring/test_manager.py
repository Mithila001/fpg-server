from __future__ import annotations

from typing import Any, Mapping

from app.algorithms.candidate_scoring import (
    CandidateEvaluator,
    CandidateScoreManager,
    CandidateScoringInput,
    EvaluationStatus,
    EvaluatorCategory,
    EvaluatorKey,
    EvaluatorRegistry,
    EvaluatorResult,
    EvaluatorRule,
    ScoringConfig,
    ScoringContext,
)


class FixedEvaluator(CandidateEvaluator):
    def __init__(self, key: str, score: float) -> None:
        self._key = EvaluatorKey(key)
        self._score = score

    @property
    def key(self) -> EvaluatorKey:
        return self._key

    def evaluate(
        self,
        context: ScoringContext,
        settings: Mapping[str, Any],
    ) -> EvaluatorResult:
        return EvaluatorResult(
            evaluator_key=self.key,
            status=EvaluationStatus.COMPLETED,
            score=self._score,
        )


def test_quality_weights_are_normalized() -> None:
    registry = EvaluatorRegistry(
        [FixedEvaluator("a", 80), FixedEvaluator("b", 40)]
    )
    config = ScoringConfig(
        evaluator_rules=(
            EvaluatorRule(
                key=EvaluatorKey("a"),
                category=EvaluatorCategory.QUALITY,
                weight=3,
            ),
            EvaluatorRule(
                key=EvaluatorKey("b"),
                category=EvaluatorCategory.QUALITY,
                weight=1,
            ),
        )
    )

    result = CandidateScoreManager(registry, config).score(
        CandidateScoringInput(specification=object(), candidate=object())
    )

    assert result.total_score == 70
    assert result.passed_critical_checks is True


def test_failed_critical_evaluator_stops_and_returns_zero() -> None:
    registry = EvaluatorRegistry(
        [FixedEvaluator("gate", 50), FixedEvaluator("quality", 100)]
    )
    config = ScoringConfig(
        evaluator_rules=(
            EvaluatorRule(
                key=EvaluatorKey("gate"),
                category=EvaluatorCategory.CRITICAL,
                minimum_score=70,
                order=1,
            ),
            EvaluatorRule(
                key=EvaluatorKey("quality"),
                category=EvaluatorCategory.QUALITY,
                weight=1,
                order=2,
            ),
        )
    )

    result = CandidateScoreManager(registry, config).score(
        CandidateScoringInput(specification=object(), candidate=object())
    )

    assert result.total_score == 0
    assert result.passed_critical_checks is False
    assert result.stopped_early is True
    assert result.evaluator_results[1].status is EvaluationStatus.SKIPPED

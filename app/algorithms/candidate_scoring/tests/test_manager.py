from __future__ import annotations

import pytest

from app.algorithms.candidate_scoring import (
    CandidateScoreManager,
    CandidateScoringInput,
    EvaluationStatus,
    EvaluatorCategory,
    EvaluatorRegistry,
    ScoringContext,
    ScoringContextFactory,
)

from .builders import build_rule, build_scoring_config, build_scoring_input
from .fakes import FakeEvaluator


def test_quality_scores_use_relative_normalized_weights() -> None:
    first = FakeEvaluator("first", score=100.0)
    second = FakeEvaluator("second", score=50.0)
    manager = CandidateScoreManager(
        registry=EvaluatorRegistry((first, second)),
        config=build_scoring_config(
            build_rule("first", weight=1.0),
            build_rule("second", weight=3.0),
        ),
    )

    result = manager.score(build_scoring_input())

    first_result, second_result = result.evaluator_results
    assert first_result.normalized_weight == pytest.approx(0.25)
    assert first_result.contribution == pytest.approx(25.0)
    assert second_result.normalized_weight == pytest.approx(0.75)
    assert second_result.contribution == pytest.approx(37.5)
    assert result.total_score == pytest.approx(62.5)


def test_not_applicable_quality_evaluator_is_excluded_and_weights_are_renormalized() -> None:
    applicable = FakeEvaluator("applicable", score=80.0)
    not_applicable = FakeEvaluator(
        "not_applicable",
        status=EvaluationStatus.NOT_APPLICABLE,
        score=None,
    )
    manager = CandidateScoreManager(
        registry=EvaluatorRegistry((applicable, not_applicable)),
        config=build_scoring_config(
            build_rule("applicable", weight=1.0),
            build_rule("not_applicable", weight=9.0),
        ),
    )

    result = manager.score(build_scoring_input())

    assert result.total_score == pytest.approx(80.0)
    assert result.evaluator_results[0].normalized_weight == pytest.approx(1.0)
    assert result.evaluator_results[1].normalized_weight == pytest.approx(0.0)
    assert result.evaluator_results[1].contribution == pytest.approx(0.0)


def test_not_applicable_quality_can_contribute_zero_when_explicitly_enabled() -> None:
    applicable = FakeEvaluator("applicable", score=100.0)
    not_applicable = FakeEvaluator(
        "not_applicable",
        status=EvaluationStatus.NOT_APPLICABLE,
        score=None,
    )
    manager = CandidateScoreManager(
        registry=EvaluatorRegistry((applicable, not_applicable)),
        config=build_scoring_config(
            build_rule("applicable", weight=1.0),
            build_rule("not_applicable", weight=1.0),
            not_applicable_quality_contributes=True,
        ),
    )

    result = manager.score(build_scoring_input())

    assert result.total_score == pytest.approx(50.0)
    assert result.evaluator_results[0].normalized_weight == pytest.approx(0.5)
    assert result.evaluator_results[1].normalized_weight == pytest.approx(0.5)
    assert result.evaluator_results[1].contribution == pytest.approx(0.0)


def test_manager_runs_critical_rules_before_quality_rules_and_respects_order() -> None:
    execution_log: list[str] = []
    evaluators = (
        FakeEvaluator("quality_late", score=90.0, execution_log=execution_log),
        FakeEvaluator("critical_b", score=90.0, execution_log=execution_log),
        FakeEvaluator("quality_early", score=90.0, execution_log=execution_log),
        FakeEvaluator("critical_a", score=90.0, execution_log=execution_log),
    )
    manager = CandidateScoreManager(
        registry=EvaluatorRegistry(evaluators),
        config=build_scoring_config(
            build_rule("quality_late", order=50),
            build_rule(
                "critical_b",
                category=EvaluatorCategory.CRITICAL,
                order=20,
                minimum_score=50.0,
            ),
            build_rule("quality_early", order=10),
            build_rule(
                "critical_a",
                category=EvaluatorCategory.CRITICAL,
                order=10,
                minimum_score=50.0,
            ),
        ),
    )

    result = manager.score(build_scoring_input())

    assert execution_log == [
        "critical_a",
        "critical_b",
        "quality_early",
        "quality_late",
    ]
    assert [str(item.evaluator_key) for item in result.evaluator_results] == execution_log


def test_passing_critical_evaluator_allows_quality_scoring() -> None:
    critical = FakeEvaluator("critical", score=70.0)
    quality = FakeEvaluator("quality", score=84.0)
    manager = CandidateScoreManager(
        registry=EvaluatorRegistry((critical, quality)),
        config=build_scoring_config(
            build_rule(
                "critical",
                category=EvaluatorCategory.CRITICAL,
                minimum_score=70.0,
            ),
            build_rule("quality"),
        ),
    )

    result = manager.score(build_scoring_input())

    assert result.passed_critical_checks is True
    assert result.stopped_early is False
    assert result.total_score == pytest.approx(84.0)
    assert result.evaluator_results[0].passed_threshold is True
    assert critical.call_count == 1
    assert quality.call_count == 1


def test_not_applicable_critical_evaluator_is_treated_as_passed() -> None:
    critical = FakeEvaluator(
        "critical",
        status=EvaluationStatus.NOT_APPLICABLE,
        score=None,
    )
    quality = FakeEvaluator("quality", score=75.0)
    manager = CandidateScoreManager(
        registry=EvaluatorRegistry((critical, quality)),
        config=build_scoring_config(
            build_rule(
                "critical",
                category=EvaluatorCategory.CRITICAL,
                minimum_score=80.0,
            ),
            build_rule("quality"),
        ),
    )

    result = manager.score(build_scoring_input())

    assert result.passed_critical_checks is True
    assert result.total_score == pytest.approx(75.0)
    assert result.evaluator_results[0].passed_threshold is True


def test_failed_critical_evaluator_stops_immediately_and_marks_remaining_rules_skipped() -> None:
    failed = FakeEvaluator("critical_failed", score=49.0)
    later_critical = FakeEvaluator("critical_later", score=100.0)
    quality = FakeEvaluator("quality", score=100.0)
    manager = CandidateScoreManager(
        registry=EvaluatorRegistry((failed, later_critical, quality)),
        config=build_scoring_config(
            build_rule(
                "critical_failed",
                category=EvaluatorCategory.CRITICAL,
                order=10,
                minimum_score=50.0,
            ),
            build_rule(
                "critical_later",
                category=EvaluatorCategory.CRITICAL,
                order=20,
                minimum_score=50.0,
            ),
            build_rule("quality", order=30),
        ),
    )

    result = manager.score(build_scoring_input())

    assert result.total_score == 0.0
    assert result.passed_critical_checks is False
    assert result.stopped_early is True
    assert "critical_failed" in (result.stop_reason or "")
    assert [item.status for item in result.evaluator_results] == [
        EvaluationStatus.COMPLETED,
        EvaluationStatus.SKIPPED,
        EvaluationStatus.SKIPPED,
    ]
    assert failed.call_count == 1
    assert later_critical.call_count == 0
    assert quality.call_count == 0
    assert result.findings[0].code == "CRITICAL_EVALUATOR_FAILED"


def test_non_fail_fast_mode_executes_all_critical_rules_before_stopping_quality() -> None:
    failed = FakeEvaluator("critical_failed", score=40.0)
    later_critical = FakeEvaluator("critical_later", score=90.0)
    quality = FakeEvaluator("quality", score=100.0)
    manager = CandidateScoreManager(
        registry=EvaluatorRegistry((failed, later_critical, quality)),
        config=build_scoring_config(
            build_rule(
                "critical_failed",
                category=EvaluatorCategory.CRITICAL,
                order=10,
                minimum_score=50.0,
            ),
            build_rule(
                "critical_later",
                category=EvaluatorCategory.CRITICAL,
                order=20,
                minimum_score=50.0,
            ),
            build_rule("quality"),
            fail_fast_on_critical_failure=False,
        ),
    )

    result = manager.score(build_scoring_input())

    assert failed.call_count == 1
    assert later_critical.call_count == 1
    assert quality.call_count == 0
    assert [item.status for item in result.evaluator_results] == [
        EvaluationStatus.COMPLETED,
        EvaluationStatus.COMPLETED,
        EvaluationStatus.SKIPPED,
    ]
    assert result.total_score == 0.0


def test_quality_evaluator_error_is_reported_and_excluded_from_weighting() -> None:
    broken = FakeEvaluator("broken", error=RuntimeError("boom"))
    healthy = FakeEvaluator("healthy", score=73.0)
    manager = CandidateScoreManager(
        registry=EvaluatorRegistry((broken, healthy)),
        config=build_scoring_config(
            build_rule("broken", weight=9.0),
            build_rule("healthy", weight=1.0),
        ),
    )

    result = manager.score(build_scoring_input())

    broken_result, healthy_result = result.evaluator_results
    assert broken_result.status is EvaluationStatus.ERROR
    assert broken_result.contribution == 0.0
    assert broken_result.findings[0].code == "EVALUATOR_ERROR"
    assert healthy_result.normalized_weight == pytest.approx(1.0)
    assert result.total_score == pytest.approx(73.0)


def test_evaluator_error_is_reraised_when_configured() -> None:
    broken = FakeEvaluator("broken", error=RuntimeError("boom"))
    manager = CandidateScoreManager(
        registry=EvaluatorRegistry((broken,)),
        config=build_scoring_config(
            build_rule("broken"),
            raise_on_evaluator_error=True,
        ),
    )

    with pytest.raises(RuntimeError, match="boom"):
        manager.score(build_scoring_input())


def test_disabled_rule_is_not_executed_or_required_in_registry() -> None:
    enabled = FakeEvaluator("enabled", score=88.0)
    manager = CandidateScoreManager(
        registry=EvaluatorRegistry((enabled,)),
        config=build_scoring_config(
            build_rule("unregistered_disabled", enabled=False),
            build_rule("enabled"),
        ),
    )

    result = manager.score(build_scoring_input())

    assert [str(item.evaluator_key) for item in result.evaluator_results] == ["enabled"]
    assert result.total_score == pytest.approx(88.0)


def test_context_factory_builds_once_and_shared_context_reaches_every_evaluator() -> None:
    class DerivedContextFactory(ScoringContextFactory):
        def __init__(self) -> None:
            self.call_count = 0

        def build(self, scoring_input: CandidateScoringInput) -> ScoringContext:
            self.call_count += 1
            return ScoringContext(
                scoring_input=scoring_input,
                derived={"prepared_once": 42},
            )

    first = FakeEvaluator("first", score=70.0)
    second = FakeEvaluator("second", score=80.0)
    factory = DerivedContextFactory()
    manager = CandidateScoreManager(
        registry=EvaluatorRegistry((first, second)),
        config=build_scoring_config(
            build_rule("first"),
            build_rule("second"),
        ),
        context_factory=factory,
    )

    manager.score(build_scoring_input())

    assert factory.call_count == 1
    assert first.received_contexts[0] is second.received_contexts[0]
    assert first.received_contexts[0].derived["prepared_once"] == 42

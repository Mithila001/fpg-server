from __future__ import annotations

import pytest

from app.algorithms.candidate_scoring import (
    CandidateScoringInput,
    EvaluationStatus,
    ScoringResult,
    evaluate_candidate,
)
from app.algorithms.candidate_scoring.evaluators import (
    EXTERIOR_CLEARANCE_KEY,
    RELATIONSHIP_QUALITY_KEY,
    SPATIAL_DISTRIBUTION_KEY,
    ZONE_SUITABILITY_KEY,
)
from app.algorithms.candidate_scoring.registry import EvaluatorRegistry
from app.algorithms.candidate_scoring.config import ScoringConfig


def test_public_api_accepts_valid_typed_input_and_returns_complete_contract(
    valid_scoring_input: CandidateScoringInput,
    default_registry: EvaluatorRegistry,
    default_config: ScoringConfig,
) -> None:
    result = evaluate_candidate(
        valid_scoring_input,
        registry=default_registry,
        config=default_config,
    )

    assert isinstance(result, ScoringResult)
    assert 0.0 <= result.total_score <= 100.0
    assert result.passed_critical_checks is True
    assert result.stopped_early is False
    assert result.stop_reason is None
    assert result.findings == ()
    assert tuple(item.evaluator_key for item in result.evaluator_results) == (
        ZONE_SUITABILITY_KEY,
        EXTERIOR_CLEARANCE_KEY,
        RELATIONSHIP_QUALITY_KEY,
        SPATIAL_DISTRIBUTION_KEY,
    )
    assert all(
        item.status in {EvaluationStatus.COMPLETED, EvaluationStatus.NOT_APPLICABLE}
        for item in result.evaluator_results
    )
    assert all(0.0 <= item.contribution <= 100.0 for item in result.evaluator_results)


def test_public_api_accepts_mapping_based_input(
    mapping_scoring_input: CandidateScoringInput,
    default_registry: EvaluatorRegistry,
    default_config: ScoringConfig,
) -> None:
    result = evaluate_candidate(
        mapping_scoring_input,
        registry=default_registry,
        config=default_config,
    )

    assert isinstance(result, ScoringResult)
    assert len(result.evaluator_results) == 4
    assert 0.0 <= result.total_score <= 100.0


def test_public_api_is_deterministic_for_identical_input(
    valid_scoring_input: CandidateScoringInput,
    default_registry: EvaluatorRegistry,
    default_config: ScoringConfig,
) -> None:
    first = evaluate_candidate(
        valid_scoring_input,
        registry=default_registry,
        config=default_config,
    )
    second = evaluate_candidate(
        valid_scoring_input,
        registry=default_registry,
        config=default_config,
    )

    assert second.total_score == pytest.approx(first.total_score)
    assert second.evaluator_results == first.evaluator_results
    assert second.findings == first.findings

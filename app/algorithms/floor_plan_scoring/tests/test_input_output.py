from __future__ import annotations

import json

import pytest

from app.algorithms.floor_plan_scoring import (
    DEFAULT_SCORING_PROFILE,
    EvaluationStatus,
    FloorPlanScoringResult,
    score_floor_plan,
)
from app.algorithms.types_new import FloorPlan, FloorPlanGenerationSpec

from .serialization import to_json_compatible


def test_public_api_accepts_types_new_and_returns_complete_contract(
    realistic_case: tuple[FloorPlan, FloorPlanGenerationSpec],
) -> None:
    floor_plan, specification = realistic_case

    result = score_floor_plan(floor_plan, specification, DEFAULT_SCORING_PROFILE)

    assert isinstance(floor_plan, FloorPlan)
    assert isinstance(specification, FloorPlanGenerationSpec)
    assert isinstance(result, FloorPlanScoringResult)
    assert 0.0 <= result.total_score <= 100.0
    assert result.passed_critical is True
    assert result.critical_failure is None

    expected_group_count = sum(
        1 for group in DEFAULT_SCORING_PROFILE.groups if group.enabled
    )
    expected_evaluator_keys = {
        str(rule.key)
        for rule in DEFAULT_SCORING_PROFILE.evaluators
        if rule.enabled
    }

    assert len(result.group_results) == expected_group_count
    assert {str(item.evaluator_key) for item in result.evaluator_results} == (
        expected_evaluator_keys
    )
    assert all(
        item.status is EvaluationStatus.COMPLETED
        for item in result.evaluator_results
    )
    assert sum(item.contribution for item in result.group_results) == pytest.approx(
        result.total_score
    )

    encoded = json.dumps(to_json_compatible(result), sort_keys=True)
    assert '"total_score"' in encoded
    assert '"evaluator_results"' in encoded


def test_scoring_is_deterministic_for_identical_realistic_input(
    realistic_case: tuple[FloorPlan, FloorPlanGenerationSpec],
) -> None:
    floor_plan, specification = realistic_case

    first = score_floor_plan(floor_plan, specification, DEFAULT_SCORING_PROFILE)
    second = score_floor_plan(floor_plan, specification, DEFAULT_SCORING_PROFILE)

    assert to_json_compatible(first) == to_json_compatible(second)

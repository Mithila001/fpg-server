from __future__ import annotations

from app.algorithms.floor_plan_scoring import (
    BEDROOM_QUALITY_KEY,
    CRITICAL_GROUP,
    FUNCTIONAL_GROUP,
    REQUIRED_ADJACENCY_KEY,
    EvaluationStatus,
    GroupStatus,
    score_floor_plan,
)
from app.algorithms.types_new import FloorPlan, FloorPlanGenerationSpec

from .builders import (
    build_broken_adjacency_spec,
    build_under_minimum_bedroom_spec,
)


def test_realistic_plan_completes_critical_and_functional_scoring(
    realistic_case: tuple[FloorPlan, FloorPlanGenerationSpec],
) -> None:
    floor_plan, specification = realistic_case

    result = score_floor_plan(floor_plan, specification)
    groups = {str(item.group_key): item for item in result.group_results}
    critical_results = [
        item
        for item in result.evaluator_results
        if item.group_key == CRITICAL_GROUP
    ]

    assert groups[str(CRITICAL_GROUP)].status is GroupStatus.COMPLETED
    assert groups[str(CRITICAL_GROUP)].raw_score == 100.0
    assert groups[str(FUNCTIONAL_GROUP)].status is GroupStatus.COMPLETED
    assert all(item.raw_score == 100.0 for item in critical_results)
    assert all(item.passed_threshold is True for item in critical_results)
    assert result.total_score > 95.0


def test_valid_but_under_sized_bedroom_reduces_functional_score(
    realistic_floor_plan: FloorPlan,
    realistic_specification: FloorPlanGenerationSpec,
) -> None:
    baseline = score_floor_plan(realistic_floor_plan, realistic_specification)
    degraded = score_floor_plan(
        realistic_floor_plan,
        build_under_minimum_bedroom_spec(),
    )
    bedroom_result = next(
        item
        for item in degraded.evaluator_results
        if item.evaluator_key == BEDROOM_QUALITY_KEY
    )

    assert degraded.passed_critical is True
    assert bedroom_result.status is EvaluationStatus.COMPLETED
    assert bedroom_result.raw_score is not None
    assert bedroom_result.raw_score < 100.0
    assert any(
        finding.code == "BEDROOM_BELOW_MINIMUM_AREA"
        and "bedroom_3" in finding.subject_ids
        for finding in bedroom_result.findings
    )
    assert degraded.total_score < baseline.total_score


def test_failed_hard_adjacency_stops_functional_scoring(
    realistic_floor_plan: FloorPlan,
) -> None:
    result = score_floor_plan(
        realistic_floor_plan,
        build_broken_adjacency_spec(),
    )
    groups = {str(item.group_key): item for item in result.group_results}
    adjacency_result = next(
        item
        for item in result.evaluator_results
        if item.evaluator_key == REQUIRED_ADJACENCY_KEY
    )
    functional_results = [
        item
        for item in result.evaluator_results
        if item.group_key == FUNCTIONAL_GROUP
    ]

    assert result.passed_critical is False
    assert result.critical_failure is not None
    assert result.critical_failure.code == "CRITICAL_SCORING_FAILED"
    assert groups[str(CRITICAL_GROUP)].status is GroupStatus.FAILED
    assert groups[str(FUNCTIONAL_GROUP)].status is GroupStatus.SKIPPED
    assert adjacency_result.raw_score == 0.0
    assert adjacency_result.passed_threshold is False
    assert any(
        finding.code == "HARD_ADJACENCY_UNSATISFIED"
        for finding in adjacency_result.findings
    )
    assert functional_results
    assert all(
        item.status is EvaluationStatus.SKIPPED
        for item in functional_results
    )
    assert result.total_score == groups[str(CRITICAL_GROUP)].contribution

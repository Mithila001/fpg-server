from __future__ import annotations

from typing import Any

from app.artifacts import (
    ArtifactFormat,
    ArtifactKind,
    ArtifactScope,
    ArtifactStorage,
    ArtifactWriteRequest,
    FeatureKey,
    WriteMode,
)
from app.core.execution import ExecutionContext
from app.util.logger import BaseLogger, LogLevel

from .events import FloorPlanScoringEvent

from ..types import (
    CRITICAL_GROUP,
    EvaluationStatus,
    EvaluatorExecutionResult,
    FloorPlanScoringResult,
    ScoreFinding,
    ScoreMetric,
    ScoringGroupResult,
)

_LOG_TAG = "floor_plan_scoring"


def log_floor_plan_scoring_result(
    result: FloorPlanScoringResult,
    *,
    context: ExecutionContext,
    request_id: str,
    candidate_id: int,
    search_trial_id: int | None,
    candidate_score: float,
    solver_run_id: int,
    usable_threshold: float,
    presentable_threshold: float,
) -> None:
    """Store the detailed diagnosis once and log a concise flow event."""

    classification = _classify_score(
        result,
        usable_threshold=usable_threshold,
        presentable_threshold=presentable_threshold,
    )

    problem_evaluators = tuple(
        execution
        for execution in result.evaluator_results
        if _is_problem_evaluator(execution)
    )

    failed_critical_evaluators = tuple(
        execution
        for execution in result.evaluator_results
        if execution.group_key == CRITICAL_GROUP
        and execution.status is EvaluationStatus.COMPLETED
        and execution.passed_threshold is False
    )

    detail = {
            "request_id": request_id,
            "candidate_id": candidate_id,
            "search_trial_id": search_trial_id,
            "candidate_score": candidate_score,
            "solver_run_id": solver_run_id,
            "total_score": result.total_score,
            "classification": classification,
            "passed_critical": result.passed_critical,
            "usable_threshold": usable_threshold,
            "presentable_threshold": presentable_threshold,
            "failed_critical_evaluator_keys": [
                str(execution.evaluator_key) for execution in failed_critical_evaluators
            ],
            "problem_evaluator_keys": [
                str(execution.evaluator_key) for execution in problem_evaluators
            ],
            "critical_failure": _finding_payload(result.critical_failure),
            "groups": [_group_payload(group) for group in result.group_results],
            "evaluators": [
                _evaluator_payload(execution) for execution in result.evaluator_results
            ],
            "findings": [_finding_payload(finding) for finding in result.findings],
        }
    logger = BaseLogger()
    try:
        reference = ArtifactStorage().save_json(
            ArtifactWriteRequest(
                feature=FeatureKey.FLOOR_PLAN_SCORING,
                artifact_kind=ArtifactKind.SCORE_BREAKDOWN,
                artifact_format=ArtifactFormat.JSON,
                artifact_scope=ArtifactScope.SOLVER_RUN,
                semantic_name="scoring",
                execution_context=context,
                write_mode=WriteMode.REPLACE,
            ),
            detail,
        )
    except Exception as exc:
        logger.log(
            feature=FeatureKey.FLOOR_PLAN_SCORING,
            event=FloorPlanScoringEvent.ARTIFACT_FAILED.value,
            level=LogLevel.ERROR,
            context=context,
            payload={
                "candidate_id": candidate_id,
                "solver_run_id": solver_run_id,
            },
            exception=exc,
        )
        return

    logger.log(
        feature=FeatureKey.FLOOR_PLAN_SCORING,
        event=FloorPlanScoringEvent.RESULT_RECORDED.value,
        level=(
            LogLevel.WARNING
            if classification in {"critical_failed", "below_usable"}
            else LogLevel.INFO
        ),
        context=context,
        payload={
            "candidate_id": candidate_id,
            "search_trial_id": search_trial_id,
            "solver_run_id": solver_run_id,
            "total_score": result.total_score,
            "classification": classification,
            "passed_critical": result.passed_critical,
            "artifact": reference.relative_path,
        },
    )


def _classify_score(
    result: FloorPlanScoringResult,
    *,
    usable_threshold: float,
    presentable_threshold: float,
) -> str:
    if not result.passed_critical:
        return "critical_failed"

    if result.total_score < usable_threshold:
        return "below_usable"

    if result.total_score >= presentable_threshold:
        return "presentable"

    return "usable"


def _is_problem_evaluator(
    execution: EvaluatorExecutionResult,
) -> bool:
    if execution.status is EvaluationStatus.SKIPPED:
        return True

    if execution.status is not EvaluationStatus.COMPLETED:
        return False

    return (
        execution.passed_threshold is False
        or bool(execution.findings)
        or (execution.raw_score is not None and execution.raw_score < 100.0)
    )


def _group_payload(
    group: ScoringGroupResult,
) -> dict[str, Any]:
    return {
        "group_key": str(group.group_key),
        "status": group.status.value,
        "normalized_maximum": group.normalized_maximum,
        "raw_score": group.raw_score,
        "contribution": group.contribution,
    }


def _evaluator_payload(
    execution: EvaluatorExecutionResult,
) -> dict[str, Any]:
    return {
        "evaluator_key": str(execution.evaluator_key),
        "group_key": str(execution.group_key),
        "status": execution.status.value,
        "raw_score": execution.raw_score,
        "configured_weight": execution.configured_weight,
        "normalized_weight": execution.normalized_weight,
        "contribution": execution.contribution,
        "threshold": execution.threshold,
        "passed_threshold": execution.passed_threshold,
        "metrics": [_metric_payload(metric) for metric in execution.metrics],
        "findings": [_finding_payload(finding) for finding in execution.findings],
    }


def _finding_payload(
    finding: ScoreFinding | None,
) -> dict[str, Any] | None:
    if finding is None:
        return None

    return {
        "code": finding.code,
        "message": finding.message,
        "severity": finding.severity.value,
        "subject_ids": list(finding.subject_ids),
        "metrics": [_metric_payload(metric) for metric in finding.metrics],
    }


def _metric_payload(
    metric: ScoreMetric,
) -> dict[str, Any]:
    return {
        "name": metric.name,
        "value": metric.value,
        "unit": metric.unit,
    }

from __future__ import annotations

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

from ..types import ScoringResult
from .events import CandidateScoringEvent


def log_candidate_scoring_event(
    context: ExecutionContext | None,
    event: CandidateScoringEvent,
    *,
    level: str = "INFO",
    payload: dict[str, object] | None = None,
    exception: BaseException | None = None,
) -> None:
    if context is None:
        return
    BaseLogger().log(
        feature=FeatureKey.CANDIDATE_SCORING,
        event=event.value,
        level=LogLevel(level),
        context=context,
        payload=payload,
        exception=exception,
    )


def record_candidate_scoring_result(
    context: ExecutionContext | None,
    result: ScoringResult,
) -> None:
    artifact: str | None = None
    if context is not None:
        try:
            reference = ArtifactStorage().save_json(
                ArtifactWriteRequest(
                    feature=FeatureKey.CANDIDATE_SCORING,
                    artifact_kind=ArtifactKind.SCORE_BREAKDOWN,
                    artifact_format=ArtifactFormat.JSON,
                    artifact_scope=(
                        ArtifactScope.SEARCH_TRIAL
                        if context.search_trial_id is not None
                        else ArtifactScope.FLOW
                    ),
                    semantic_name="scoring",
                    execution_context=context,
                    write_mode=WriteMode.REPLACE,
                ),
                _result_payload(result),
            )
            artifact = reference.relative_path
        except Exception as exc:
            log_candidate_scoring_event(
                context,
                CandidateScoringEvent.ARTIFACT_FAILED,
                level="ERROR",
                exception=exc,
            )
    log_candidate_scoring_event(
        context,
        CandidateScoringEvent.COMPLETED,
        payload={
            "total_score": result.total_score,
            "passed_critical_checks": result.passed_critical_checks,
            "stopped_early": result.stopped_early,
            "artifact": artifact,
        },
    )


def _result_payload(result: ScoringResult) -> dict[str, object]:
    return {
        "total_score": result.total_score,
        "passed_critical_checks": result.passed_critical_checks,
        "stopped_early": result.stopped_early,
        "stop_reason": result.stop_reason,
        "evaluators": [
            {
                "evaluator_key": str(item.evaluator_key),
                "category": item.category.value,
                "status": item.status.value,
                "raw_score": item.raw_score,
                "configured_weight": item.configured_weight,
                "normalized_weight": item.normalized_weight,
                "contribution": item.contribution,
                "threshold": item.threshold,
                "passed_threshold": item.passed_threshold,
                "metrics": dict(item.metrics),
                "findings": [
                    {
                        "code": finding.code,
                        "message": finding.message,
                        "severity": finding.severity.value,
                        "subject_ids": list(finding.subject_ids),
                    }
                    for finding in item.findings
                ],
            }
            for item in result.evaluator_results
        ],
    }

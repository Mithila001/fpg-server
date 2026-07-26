from __future__ import annotations

from typing import Any

from app.artifacts import FeatureKey
from app.artifacts import (
    ArtifactFormat,
    ArtifactKind,
    ArtifactScope,
    ArtifactStorage,
    ArtifactWriteRequest,
    WriteMode,
)
from app.core.execution import ExecutionContext
from app.util.logger import BaseLogger, LogLevel


def log_pipeline_event(
    context: ExecutionContext,
    event: str,
    *,
    level: str = "INFO",
    payload: dict[str, Any] | None = None,
    exception: BaseException | None = None,
) -> None:
    BaseLogger().log(
        feature=FeatureKey.PIPELINE,
        event=event,
        level=LogLevel(level),
        context=context,
        payload=payload,
        exception=exception,
    )


def create_pipeline_context(
    *,
    job_id: str,
    seed: int | None = None,
) -> ExecutionContext:
    return ArtifactStorage().create_execution_context(job_id=job_id, seed=seed)


def save_final_floor_plan(
    context: ExecutionContext,
    floor_plan: Any,
) -> str | None:
    reference = ArtifactStorage().save_json(
        ArtifactWriteRequest(
            feature=FeatureKey.PIPELINE,
            artifact_kind=ArtifactKind.FINAL_RESULT,
            artifact_format=ArtifactFormat.JSON,
            artifact_scope=ArtifactScope.FLOW,
            semantic_name="final_floor_plan",
            execution_context=context,
            write_mode=WriteMode.REPLACE,
        ),
        floor_plan,
    )
    return reference.relative_path

from __future__ import annotations

from app.algorithms.types_new import BuildableSpaceRequestData, BuildableSpaceResult
from app.artifacts import ArtifactStorage
from app.core.execution import ExecutionContext
from app.pipeline.buildable_space import (
    BuildableSpaceContext,
    run_buildable_space_pipeline,
)


def execute_buildable_space(
    request: BuildableSpaceRequestData,
    *,
    execution_context: ExecutionContext | None = None,
) -> BuildableSpaceResult:
    resolved_context = (
        execution_context
        if execution_context is not None
        else ArtifactStorage().create_execution_context()
    )
    return run_buildable_space_pipeline(
        request,
        BuildableSpaceContext(execution_context=resolved_context),
    )

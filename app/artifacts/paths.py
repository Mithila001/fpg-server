from __future__ import annotations

from pathlib import Path

from app.core.execution import flow_directory_name, normalize_slug

from .config import ArtifactStorageConfig
from .enums import ArtifactKind, ArtifactScope
from .models import ArtifactWriteRequest


def resolve_artifact_path(
    config: ArtifactStorageConfig,
    request: ArtifactWriteRequest,
) -> Path:
    name = normalize_slug(request.semantic_name)
    extension = request.artifact_format.value

    if request.artifact_scope is ArtifactScope.GLOBAL:
        date = normalize_slug(request.metadata.get("event_date", "undated"))
        return (
            config.output_root
            / "application"
            / "json"
            / date
            / f"{name}.{extension}"
        )

    context = request.execution_context
    assert context is not None
    flow_root = config.output_root / "flows" / flow_directory_name(
        started_at=context.flow_started_at,
        flow_id=str(context.flow_id),
    )

    if request.artifact_kind is ArtifactKind.EVENT_LOG:
        return (
            flow_root
            / "json"
            / "logs"
            / f"{normalize_slug(request.feature.value)}.json"
        )

    directory = flow_root / request.artifact_format.value / normalize_slug(
        request.feature.value
    )
    prefix = _identity_prefix(request)
    return directory / f"{prefix}{name}.{extension}"


def _identity_prefix(request: ArtifactWriteRequest) -> str:
    context = request.execution_context
    assert context is not None
    if request.artifact_scope is ArtifactScope.SEARCH_TRIAL:
        if context.search_trial_id is None:
            raise ValueError("search-trial artifacts require search_trial_id")
        return f"trial_{int(context.search_trial_id):03d}_"
    if request.artifact_scope is ArtifactScope.CANDIDATE:
        if context.candidate_id is None:
            raise ValueError("candidate artifacts require candidate_id")
        return f"candidate_{int(context.candidate_id):03d}_"
    if request.artifact_scope is ArtifactScope.SOLVER_RUN:
        if context.candidate_id is None or context.solver_run_id is None:
            raise ValueError(
                "solver-run artifacts require candidate_id and solver_run_id"
            )
        return (
            f"candidate_{int(context.candidate_id):03d}_"
            f"solver_run_{int(context.solver_run_id):02d}_"
        )
    return ""

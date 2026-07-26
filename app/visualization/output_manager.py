from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

from matplotlib.figure import Figure

from app.artifacts import (
    ArtifactFormat,
    ArtifactKind,
    ArtifactScope,
    ArtifactStorage,
    ArtifactStorageConfig,
    ArtifactWriteRequest,
    FeatureKey,
    WriteMode,
)
from app.core.execution import ExecutionContext

from .config import RenderConfig
from .matplotlib_backend.renderer import close_figure


@dataclass(slots=True)
class VisualizationOutputManager:
    root_directory: Path
    _compatibility_contexts: dict[tuple[str, str | None], ExecutionContext] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )

    def save_png(
        self,
        figure: Figure,
        *,
        feature: str,
        config: RenderConfig,
        run_id: str | None = None,
        run_timestamp: str | None = None,
        name: str | None = None,
        filename_prefix: str | None = None,
        context: ExecutionContext | None = None,
        artifact_feature: FeatureKey | None = None,
        artifact_scope: ArtifactScope | None = None,
    ) -> Path:
        """Encode a figure and persist it through the shared artifact store."""

        if name is not None and filename_prefix is not None:
            raise ValueError("use either name or filename_prefix, not both")

        storage = ArtifactStorage(
            replace(
                ArtifactStorageConfig.from_environment(),
                output_root=self.root_directory,
            )
        )
        active_context = context or self._compatibility_context(
            storage,
            run_id=run_id or feature,
            run_timestamp=run_timestamp,
        )
        try:
            buffer = BytesIO()
            figure.savefig(
                buffer,
                format="png",
                dpi=config.dpi,
                facecolor=config.background_color,
                transparent=config.transparent,
                bbox_inches=config.bbox_inches,
            )
            reference = storage.save_png(
                ArtifactWriteRequest(
                    feature=artifact_feature or _feature_key(feature),
                    artifact_kind=ArtifactKind.VISUALIZATION,
                    artifact_format=ArtifactFormat.PNG,
                    artifact_scope=artifact_scope or _context_scope(active_context),
                    semantic_name=filename_prefix or name or feature,
                    execution_context=active_context,
                    write_mode=WriteMode.REPLACE,
                ),
                buffer.getvalue(),
            )
            if reference.path is None:
                raise RuntimeError("PNG artifact output is disabled")
            return reference.path
        finally:
            close_figure(figure)

    def _compatibility_context(
        self,
        storage: ArtifactStorage,
        *,
        run_id: str,
        run_timestamp: str | None,
    ) -> ExecutionContext:
        key = (run_id, run_timestamp)
        existing = self._compatibility_contexts.get(key)
        if existing is not None:
            return existing
        context = storage.create_execution_context(
            job_id=run_id,
            started_at=_parse_compatibility_timestamp(run_timestamp),
        )
        self._compatibility_contexts[key] = context
        return context


def _parse_compatibility_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    for pattern in ("%Y%m%dT%H%M%S%fZ", "%Y%m%dT%H%M%S.%fZ"):
        try:
            return datetime.strptime(value, pattern).replace(tzinfo=UTC)
        except ValueError:
            continue
    raise ValueError("run_timestamp must be a sortable UTC timestamp")


def _context_scope(context: ExecutionContext) -> ArtifactScope:
    if context.solver_run_id is not None:
        return ArtifactScope.SOLVER_RUN
    if context.candidate_id is not None:
        return ArtifactScope.CANDIDATE
    if context.search_trial_id is not None:
        return ArtifactScope.SEARCH_TRIAL
    return ArtifactScope.FLOW


def _feature_key(feature: str) -> FeatureKey:
    aliases = {
        "candidate_search_score": FeatureKey.CANDIDATE_SCORING,
        "floor_plan_score": FeatureKey.FLOOR_PLAN_SCORING,
        "floor_plan_general": FeatureKey.FLOOR_PLAN_SOLVER,
    }
    if feature in aliases:
        return aliases[feature]
    try:
        return FeatureKey(feature)
    except ValueError:
        return FeatureKey.VISUALIZATION

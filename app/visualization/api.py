from __future__ import annotations

from pathlib import Path

from fpg_core.candidate_scoring import CandidateScoringInput, ScoringResult
from fpg_core.candidate_scoring.evaluators.exterior_clearance import (
    ExteriorClearanceVisualizationData,
)
from fpg_core.candidate_scoring.evaluators.relationship_quality import (
    RelationshipQualityVisualizationData,
)
from fpg_core.candidate_scoring.evaluators.spatial_distribution import (
    SpatialDistributionVisualizationData,
)
from fpg_core.candidate_scoring.evaluators.zone_suitability import (
    ZoneSuitabilityVisualizationData,
)
from fpg_core.floor_plan_scoring import FloorPlanScoringResult
from fpg_core.floor_plan_scoring.evaluators.enclosed_voids import (
    EnclosedVoidsVisualizationData,
)
from fpg_core.floor_plan_scoring.evaluators.inward_recess import (
    InwardRecessVisualizationData,
)
from fpg_core.types import FloorPlan
from matplotlib.figure import Figure

from app.core.execution import ExecutionContext

from .config import DEFAULT_RENDER_CONFIG, RenderConfig
from .features.candidate_search.candidate_search_render import (
    render_candidate_search_figure,
)
from .features.candidate_search.models import (
    CandidatePoint,
    CandidateSearchVisualization,
    SearchBounds,
)
from .features.floor_plan_general.floor_plan_general_render import (
    render_floor_plan_general_figure,
)
from .features.floor_plan_general.models import (
    FloorPlanFlowVisualization,
    FloorPlanVisualizationStage,
)
from .features.floor_plan_solver.floor_plan_solver_render import (
    render_floor_plan_solver_figure,
)
from .features.floor_plan_solver.models import (
    FloorPlanSolverStatus,
    FloorPlanSolverVisualization,
)
from .features.score.candidate_search_score.exterior_clearance import (
    render_exterior_clearance_figure,
)
from .features.score.candidate_search_score.relationship_quality import (
    render_relationship_scores_figure,
    render_relationship_weights_figure,
)
from .features.score.candidate_search_score.spatial_distribution import (
    render_spatial_distribution_figure,
)
from .features.score.candidate_search_score.zone_suitability import (
    render_zone_suitability_figure,
)
from .features.score.config import (
    DEFAULT_SCORING_VISUALIZATION_CONFIG,
    CandidateScoringVisualizationConfig,
    FloorPlanScoringVisualizationConfig,
    ScoringVisualizationConfig,
)
from .features.score.floor_plan_score.enclosed_voids import (
    render_enclosed_voids_figure,
)
from .features.score.floor_plan_score.inward_recess import (
    render_inward_recess_figure,
)
from .output_manager import VisualizationOutputManager


def render_candidate_search(
    payload: CandidateSearchVisualization,
    *,
    run_id: str | None = None,
    run_timestamp: str | None = None,
    output_name: str | None = None,
    output_root: str | Path | None = None,
    config: RenderConfig | None = None,
    context: ExecutionContext | None = None,
) -> Path:
    """Render a Candidate Search trial and persist it as a managed PNG."""
    render_config = config or DEFAULT_RENDER_CONFIG
    manager = VisualizationOutputManager(
        Path(output_root) if output_root is not None else render_config.output_root
    )
    figure = render_candidate_search_figure(payload, config=render_config)
    return manager.save_png(
        figure,
        feature="candidate_search",
        run_id=run_id,
        run_timestamp=run_timestamp,
        name=output_name or f"trial-{payload.trial_number}",
        config=render_config,
        context=context,
    )


def render_floor_plan_solver(
    payload: FloorPlanSolverVisualization,
    *,
    run_id: str | None = None,
    run_timestamp: str | None = None,
    output_name: str | None = None,
    output_root: str | Path | None = None,
    config: RenderConfig | None = None,
    context: ExecutionContext | None = None,
) -> Path:
    """Render one Floor Plan Solver profile result as a managed PNG."""
    render_config = config or DEFAULT_RENDER_CONFIG
    manager = VisualizationOutputManager(
        Path(output_root) if output_root is not None else render_config.output_root
    )
    figure = render_floor_plan_solver_figure(payload, config=render_config)
    return manager.save_png(
        figure,
        feature="floor_plan_solver",
        run_id=run_id,
        run_timestamp=run_timestamp,
        name=output_name or f"{payload.profile_name}-{payload.status.value}",
        config=render_config,
        context=context,
    )


def render_floor_plan_general(
    payload: FloorPlanFlowVisualization,
    *,
    run_id: str | None = None,
    run_timestamp: str | None = None,
    output_prefix: str = "floor_plan_general",
    output_root: str | Path | None = None,
    config: RenderConfig | None = None,
    context: ExecutionContext | None = None,
) -> Path:
    """Render all ordered floor-plan stages into one timestamped PNG."""
    render_config = config or DEFAULT_RENDER_CONFIG
    manager = VisualizationOutputManager(
        Path(output_root) if output_root is not None else render_config.output_root
    )
    figure = render_floor_plan_general_figure(payload, config=render_config)
    return manager.save_png(
        figure,
        feature="floor_plan_general",
        run_id=run_id,
        run_timestamp=run_timestamp,
        filename_prefix=output_prefix,
        config=render_config,
        context=context,
    )


def render_candidate_scoring_features(
    scoring_input: CandidateScoringInput,
    scoring_result: ScoringResult,
    *,
    visualization_config: ScoringVisualizationConfig = (
        DEFAULT_SCORING_VISUALIZATION_CONFIG
    ),
    run_id: str | None = None,
    run_timestamp: str | None = None,
    output_root: str | Path | None = None,
    config: RenderConfig | None = None,
    context: ExecutionContext | None = None,
) -> tuple[Path, ...]:
    """Render enabled diagnostics for one completed candidate scoring run."""
    if not visualization_config.enabled:
        return ()
    if not isinstance(scoring_input, CandidateScoringInput):
        raise TypeError("scoring_input must be a CandidateScoringInput")

    render_config = config or DEFAULT_RENDER_CONFIG
    manager = VisualizationOutputManager(
        Path(output_root) if output_root is not None else render_config.output_root
    )
    output_paths: list[Path] = []

    for execution in scoring_result.evaluator_results:
        key = str(execution.evaluator_key)
        payload = execution.visualization_payload
        if (
            key == "exterior_clearance"
            and visualization_config.candidate.exterior_clearance
            and isinstance(payload, ExteriorClearanceVisualizationData)
        ):
            output_paths.append(
                _save_score_figure(
                    manager,
                    render_exterior_clearance_figure(
                        payload,
                        config=render_config,
                    ),
                    feature="candidate_search_score",
                    name="exterior-clearance",
                    render_config=render_config,
                    run_id=run_id,
                    run_timestamp=run_timestamp,
                    context=context,
                )
            )
        elif (
            key == "relationship_quality"
            and visualization_config.candidate.relationship_quality
            and isinstance(payload, RelationshipQualityVisualizationData)
        ):
            output_paths.extend(
                (
                    _save_score_figure(
                        manager,
                        render_relationship_weights_figure(
                            payload,
                            config=render_config,
                        ),
                        feature="candidate_search_score",
                        name="relationship-quality-weights",
                        render_config=render_config,
                        run_id=run_id,
                        run_timestamp=run_timestamp,
                        context=context,
                    ),
                    _save_score_figure(
                        manager,
                        render_relationship_scores_figure(
                            payload,
                            config=render_config,
                        ),
                        feature="candidate_search_score",
                        name="relationship-quality-scores",
                        render_config=render_config,
                        run_id=run_id,
                        run_timestamp=run_timestamp,
                        context=context,
                    ),
                )
            )
        elif (
            key == "spatial_distribution"
            and visualization_config.candidate.spatial_distribution
            and isinstance(payload, SpatialDistributionVisualizationData)
        ):
            output_paths.append(
                _save_score_figure(
                    manager,
                    render_spatial_distribution_figure(
                        payload,
                        config=render_config,
                    ),
                    feature="candidate_search_score",
                    name="spatial-distribution",
                    render_config=render_config,
                    run_id=run_id,
                    run_timestamp=run_timestamp,
                    context=context,
                )
            )
        elif (
            key == "zone_suitability"
            and visualization_config.candidate.zone_suitability
            and isinstance(payload, ZoneSuitabilityVisualizationData)
        ):
            output_paths.append(
                _save_score_figure(
                    manager,
                    render_zone_suitability_figure(
                        payload,
                        config=render_config,
                    ),
                    feature="candidate_search_score",
                    name="zone-suitability",
                    render_config=render_config,
                    run_id=run_id,
                    run_timestamp=run_timestamp,
                    context=context,
                )
            )
    return tuple(output_paths)


def render_floor_plan_scoring_features(
    floor_plan: FloorPlan,
    scoring_result: FloorPlanScoringResult,
    *,
    visualization_config: ScoringVisualizationConfig = (
        DEFAULT_SCORING_VISUALIZATION_CONFIG
    ),
    run_id: str | None = None,
    run_timestamp: str | None = None,
    output_root: str | Path | None = None,
    config: RenderConfig | None = None,
    context: ExecutionContext | None = None,
) -> tuple[Path, ...]:
    """Render enabled diagnostics for one completed floor-plan scoring run."""
    if not visualization_config.enabled:
        return ()
    if not isinstance(floor_plan, FloorPlan):
        raise TypeError("floor_plan must be a FloorPlan")

    render_config = config or DEFAULT_RENDER_CONFIG
    manager = VisualizationOutputManager(
        Path(output_root) if output_root is not None else render_config.output_root
    )
    output_paths: list[Path] = []

    for execution in scoring_result.evaluator_results:
        key = str(execution.evaluator_key)
        payload = execution.visualization_payload
        if (
            key == "enclosed_voids"
            and visualization_config.floor_plan.enclosed_voids
            and isinstance(payload, EnclosedVoidsVisualizationData)
        ):
            output_paths.append(
                _save_score_figure(
                    manager,
                    render_enclosed_voids_figure(
                        floor_plan,
                        payload,
                        config=render_config,
                    ),
                    feature="floor_plan_score",
                    name="enclosed-voids",
                    render_config=render_config,
                    run_id=run_id,
                    run_timestamp=run_timestamp,
                    context=context,
                )
            )
        elif (
            key == "inward_recess"
            and visualization_config.floor_plan.inward_recess
            and isinstance(payload, InwardRecessVisualizationData)
        ):
            output_paths.append(
                _save_score_figure(
                    manager,
                    render_inward_recess_figure(
                        floor_plan,
                        payload,
                        config=render_config,
                    ),
                    feature="floor_plan_score",
                    name="inward-recess",
                    render_config=render_config,
                    run_id=run_id,
                    run_timestamp=run_timestamp,
                    context=context,
                )
            )
    return tuple(output_paths)


def _save_score_figure(
    manager: VisualizationOutputManager,
    figure: Figure,
    *,
    feature: str,
    name: str,
    render_config: RenderConfig,
    run_id: str | None,
    run_timestamp: str | None,
    context: ExecutionContext | None,
) -> Path:
    return manager.save_png(
        figure,
        feature=feature,
        run_id=run_id,
        run_timestamp=run_timestamp,
        name=name,
        config=render_config,
        context=context,
    )


__all__ = [
    "CandidatePoint",
    "CandidateSearchVisualization",
    "CandidateScoringVisualizationConfig",
    "DEFAULT_SCORING_VISUALIZATION_CONFIG",
    "FloorPlanFlowVisualization",
    "FloorPlanScoringVisualizationConfig",
    "FloorPlanSolverStatus",
    "FloorPlanSolverVisualization",
    "FloorPlanVisualizationStage",
    "ScoringVisualizationConfig",
    "SearchBounds",
    "render_candidate_search",
    "render_candidate_scoring_features",
    "render_floor_plan_general",
    "render_floor_plan_scoring_features",
    "render_floor_plan_solver",
]

from __future__ import annotations

from pathlib import Path

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
from .output_manager import VisualizationOutputManager


def render_candidate_search(
    payload: CandidateSearchVisualization,
    *,
    run_id: str | None = None,
    run_timestamp: str | None = None,
    output_name: str | None = None,
    output_root: str | Path | None = None,
    config: RenderConfig | None = None,
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
    )


def render_floor_plan_solver(
    payload: FloorPlanSolverVisualization,
    *,
    run_id: str | None = None,
    run_timestamp: str | None = None,
    output_name: str | None = None,
    output_root: str | Path | None = None,
    config: RenderConfig | None = None,
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
    )


def render_floor_plan_general(
    payload: FloorPlanFlowVisualization,
    *,
    run_id: str | None = None,
    run_timestamp: str | None = None,
    output_prefix: str = "floor_plan_general",
    output_root: str | Path | None = None,
    config: RenderConfig | None = None,
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
    )


__all__ = [
    "CandidatePoint",
    "CandidateSearchVisualization",
    "FloorPlanFlowVisualization",
    "FloorPlanSolverStatus",
    "FloorPlanSolverVisualization",
    "FloorPlanVisualizationStage",
    "SearchBounds",
    "render_candidate_search",
    "render_floor_plan_general",
    "render_floor_plan_solver",
]

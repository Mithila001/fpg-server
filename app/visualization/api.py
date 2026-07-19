from __future__ import annotations

from pathlib import Path

from .config import DEFAULT_RENDER_CONFIG, RenderConfig
from .features.candidate_search.candidate_search_render import render_candidate_search_figure
from .features.candidate_search.models import (
    CandidatePoint,
    CandidateSearchVisualization,
    SearchBounds,
)
from .output_manager import VisualizationOutputManager


def render_candidate_search(
    payload: CandidateSearchVisualization,
    *,
    run_id: str | None = None,
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
        name=output_name or f"trial-{payload.trial_number}",
        config=render_config,
    )


__all__ = [
    "CandidatePoint",
    "CandidateSearchVisualization",
    "SearchBounds",
    "render_candidate_search",
]

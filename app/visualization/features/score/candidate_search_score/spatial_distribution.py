from __future__ import annotations

from fpg_core.candidate_scoring.evaluators.spatial_distribution import (
    SpatialDistributionVisualizationData,
)
from matplotlib.figure import Figure

from ....config import RenderConfig
from ....matplotlib_backend.renderer import create_figure
from .common import configure_candidate_axes, draw_candidate_points


def render_spatial_distribution_figure(
    payload: SpatialDistributionVisualizationData,
    *,
    config: RenderConfig,
) -> Figure:
    figure, axes = create_figure(config)
    if payload.nearest_distances:
        heatmap = [
            [payload.nearest_distances[x][y] for x in range(payload.grid_size)]
            for y in range(payload.grid_size)
        ]
        image = axes.imshow(
            heatmap,
            origin="lower",
            extent=(0.0, payload.floor_width, 0.0, payload.floor_length),
            cmap="RdYlGn_r",
            vmin=0.0,
            vmax=max(
                payload.theoretical_coverage_gap * payload.gap_zero_score_ratio,
                1e-9,
            ),
            interpolation="bilinear",
            alpha=0.82,
            zorder=1,
        )
        figure.colorbar(
            image,
            ax=axes,
            label="Distance to nearest hint point",
            fraction=0.046,
            pad=0.04,
        )
    draw_candidate_points(axes, payload.points)
    configure_candidate_axes(
        axes,
        payload.floor_width,
        payload.floor_length,
        "Candidate Scoring — Spatial Distribution",
    )
    return figure

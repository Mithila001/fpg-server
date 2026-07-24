from __future__ import annotations

from matplotlib.figure import Figure

from app.algorithms.candidate_scoring.evaluators.zone_suitability import (
    ZoneSuitabilityVisualizationData,
)

from ....config import RenderConfig
from ....matplotlib_backend.renderer import create_figure
from .common import configure_candidate_axes


def render_zone_suitability_figure(
    payload: ZoneSuitabilityVisualizationData,
    *,
    config: RenderConfig,
) -> Figure:
    figure, axes = create_figure(config)
    for index in range(1, payload.grid_size):
        axes.axvline(
            payload.floor_width * index / payload.grid_size,
            color="#64748b",
            linestyle="--",
            linewidth=0.8,
            alpha=0.6,
        )
        axes.axhline(
            payload.floor_length * index / payload.grid_size,
            color="#64748b",
            linestyle="--",
            linewidth=0.8,
            alpha=0.6,
        )

    for point in payload.points:
        color = "#16a34a" if point.inside_preferred_zone else "#dc2626"
        axes.scatter(
            point.x,
            point.y,
            s=95,
            color=color,
            edgecolors="#111827",
            linewidths=0.8,
            zorder=20,
        )
        axes.annotate(
            f"{point.room_name}\n{point.score:.1f}",
            (point.x, point.y),
            xytext=(6, 6),
            textcoords="offset points",
            fontsize=8,
            color="#111827",
            zorder=30,
        )

    configure_candidate_axes(
        axes,
        payload.floor_width,
        payload.floor_length,
        "Candidate Scoring — Zone Suitability",
    )
    return figure

from __future__ import annotations

from matplotlib import colormaps
from matplotlib.colors import Normalize
from matplotlib.figure import Figure

from app.algorithms.candidate_scoring.evaluators.relationship_quality import (
    RelationshipQualityVisualizationData,
)

from ....config import RenderConfig
from ....matplotlib_backend.renderer import create_figure
from .common import configure_candidate_axes, draw_candidate_points


def render_relationship_weights_figure(
    payload: RelationshipQualityVisualizationData,
    *,
    config: RenderConfig,
) -> Figure:
    figure, axes = create_figure(config)
    points = {point.room_id: point for point in payload.points}
    maximum = max(
        (edge.relation_multiplier for edge in payload.edges),
        default=1.0,
    )
    normalizer = Normalize(vmin=0.0, vmax=max(1.0, maximum))
    color_map = colormaps["plasma"]

    for edge in payload.edges:
        source = points[edge.source_id]
        target = points[edge.target_id]
        color = color_map(normalizer(edge.relation_multiplier))
        axes.plot(
            (source.x, target.x),
            (source.y, target.y),
            color=color,
            linewidth=1.2,
            alpha=0.68,
            zorder=5,
        )
        axes.text(
            (source.x + target.x) / 2.0,
            (source.y + target.y) / 2.0,
            f"{edge.relation_multiplier:.1f}",
            fontsize=6,
            color="#374151",
            ha="center",
            va="center",
            zorder=10,
        )

    draw_candidate_points(axes, payload.points)
    configure_candidate_axes(
        axes,
        payload.floor_width,
        payload.floor_length,
        "Candidate Scoring — Relationship Weights",
    )
    return figure


def render_relationship_scores_figure(
    payload: RelationshipQualityVisualizationData,
    *,
    config: RenderConfig,
) -> Figure:
    figure, axes = create_figure(config)
    points = {point.room_id: point for point in payload.points}
    color_map = colormaps["RdYlGn"]
    lines: list[str] = []

    for query in payload.queries:
        color = color_map(max(0.0, min(1.0, query.score / 100.0)))
        if len(query.path) >= 2:
            path_points = [points[room_id] for room_id in query.path]
            axes.plot(
                [point.x for point in path_points],
                [point.y for point in path_points],
                color=color,
                linewidth=3.0,
                alpha=0.78,
                zorder=8,
            )
        lines.append(
            f"{query.start_type} → {query.end_type}: {query.score:.1f}"
        )

    draw_candidate_points(axes, payload.points)
    configure_candidate_axes(
        axes,
        payload.floor_width,
        payload.floor_length,
        "Candidate Scoring — Relationship Evaluation Scores",
    )
    if lines:
        figure.text(
            0.02,
            0.98,
            "\n".join(lines),
            ha="left",
            va="top",
            fontsize=7,
            family="monospace",
            bbox={
                "facecolor": "white",
                "edgecolor": "#64748b",
                "alpha": 0.9,
            },
        )
        figure.subplots_adjust(left=0.24)
    return figure

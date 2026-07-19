from __future__ import annotations

from matplotlib.figure import Figure

from ...config import RenderConfig
from ...matplotlib_backend.renderer import create_figure
from .models import CandidateSearchVisualization


def render_candidate_search_figure(
    payload: CandidateSearchVisualization,
    *,
    config: RenderConfig,
) -> Figure:
    """Compose the complete Candidate Search figure without persisting it."""
    figure, axes = create_figure(config)
    bounds = payload.bounds

    for point in payload.points:
        axes.scatter(
            point.x, point.y, s=70, color="#2563eb", edgecolors="#1e3a8a",
            linewidths=0.7, zorder=10,
        )
        axes.annotate(
            point.room_id, (point.x, point.y), xytext=(6, 6),
            textcoords="offset points", fontsize=8, color="#111827", zorder=20,
        )

    axes.set_xlim(bounds.min_x, bounds.max_x)
    axes.set_ylim(bounds.min_y, bounds.max_y)
    axes.set_aspect("equal", adjustable="box")
    axes.set_xlabel("X (project units)")
    axes.set_ylabel("Y (project units)")
    axes.set_xticks(range(bounds.min_x, bounds.max_x + 1, payload.grid_resolution))
    axes.set_yticks(range(bounds.min_y, bounds.max_y + 1, payload.grid_resolution))
    axes.grid(linestyle="--", linewidth=0.5, color="#94a3b8", alpha=0.55, zorder=0)
    axes.set_title(
        f"Candidate Search Trial {payload.trial_number}",
        fontsize=14, weight="bold", pad=16,
    )

    configured_trials = payload.trial_count if payload.trial_count is not None else "-"
    info = (
        f"Trial : {payload.trial_number}\n"
        f"Score : {payload.score:.3f}\n"
        f"Points : {len(payload.points)}\n"
        f"Bounds : ({bounds.min_x}, {bounds.min_y}) -> "
        f"({bounds.max_x}, {bounds.max_y})\n"
        f"Grid : {payload.grid_resolution}\n"
        f"Configured Trials : {configured_trials}"
    )
    figure.text(
        0.02, 0.97, info, fontsize=10, va="top", family="monospace",
        bbox={"facecolor": "white", "edgecolor": "#64748b", "alpha": 0.92},
    )
    figure.subplots_adjust(left=0.12, right=0.96, bottom=0.10, top=0.82)
    return figure

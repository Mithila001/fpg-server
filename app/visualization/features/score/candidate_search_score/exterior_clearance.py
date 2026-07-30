from __future__ import annotations

from fpg_core.candidate_scoring.evaluators.exterior_clearance import (
    ExteriorClearanceVisualizationData,
)
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from ....config import RenderConfig
from ....matplotlib_backend.renderer import create_figure
from .common import configure_candidate_axes, draw_candidate_points


def render_exterior_clearance_figure(
    payload: ExteriorClearanceVisualizationData,
    *,
    config: RenderConfig,
) -> Figure:
    figure, axes = create_figure(config)
    blocker_ids = {
        blocker_id
        for corridor in payload.corridors
        for blocker_id in corridor.blocker_ids
    }
    draw_candidate_points(
        axes,
        payload.points,
        colors={room_id: "#dc2626" for room_id in blocker_ids},
    )

    for corridor in payload.corridors:
        min_x, max_x, min_y, max_y = corridor.bounds
        selected = corridor.selected_for_score
        blocked = bool(corridor.blocker_ids)
        color = "#dc2626" if blocked else "#16a34a"
        axes.add_patch(
            Rectangle(
                (min_x, min_y),
                max_x - min_x,
                max_y - min_y,
                facecolor=color,
                edgecolor=color,
                alpha=0.18 if selected else 0.07,
                linewidth=2.0 if selected else 1.0,
                linestyle="-" if selected else "--",
                zorder=5,
            )
        )
        axes.text(
            (min_x + max_x) / 2.0,
            (min_y + max_y) / 2.0,
            f"{corridor.room_name}\n{corridor.side}",
            ha="center",
            va="center",
            fontsize=7,
            color="#111827",
            zorder=10,
        )

    configure_candidate_axes(
        axes,
        payload.floor_width,
        payload.floor_length,
        "Candidate Scoring — Exterior Clearance",
    )
    if payload.corridors:
        min_x = min(0.0, *(corridor.bounds[0] for corridor in payload.corridors))
        max_x = max(
            payload.floor_width,
            *(corridor.bounds[1] for corridor in payload.corridors),
        )
        min_y = min(0.0, *(corridor.bounds[2] for corridor in payload.corridors))
        max_y = max(
            payload.floor_length,
            *(corridor.bounds[3] for corridor in payload.corridors),
        )
        padding = max(max_x - min_x, max_y - min_y) * 0.04
        axes.set_xlim(min_x - padding, max_x + padding)
        axes.set_ylim(min_y - padding, max_y + padding)
    return figure

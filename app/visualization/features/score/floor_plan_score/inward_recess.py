from __future__ import annotations

from matplotlib.figure import Figure
from matplotlib.patches import Polygon as PolygonPatch

from app.algorithms.floor_plan_scoring.evaluators.inward_recess import (
    InwardRecessVisualizationData,
)
from app.algorithms.types_new import FloorPlan

from ....config import RenderConfig
from ....matplotlib_backend.renderer import create_figure
from .common import draw_floor_plan


def render_inward_recess_figure(
    floor_plan: FloorPlan,
    payload: InwardRecessVisualizationData,
    *,
    config: RenderConfig,
) -> Figure:
    figure, axes = create_figure(config)
    draw_floor_plan(
        axes,
        floor_plan,
        "Floor Plan Scoring — Inward Recesses",
    )
    for pocket in payload.pockets:
        color = "#dc2626" if pocket.violates_maximum else "#f59e0b"
        axes.add_patch(
            PolygonPatch(
                pocket.points,
                closed=True,
                facecolor=color,
                edgecolor="#7f1d1d" if pocket.violates_maximum else "#92400e",
                linewidth=1.7,
                alpha=0.62,
                zorder=20,
            )
        )
        center_x = sum(x for x, _ in pocket.points) / len(pocket.points)
        center_y = sum(y for _, y in pocket.points) / len(pocket.points)
        axes.text(
            center_x,
            center_y,
            f"Pocket {pocket.pocket_index}\n{pocket.measured_length:.2f}",
            ha="center",
            va="center",
            fontsize=8,
            weight="bold",
            color="#ffffff",
            zorder=25,
        )
    return figure

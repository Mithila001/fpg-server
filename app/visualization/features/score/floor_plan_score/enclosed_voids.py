from __future__ import annotations

from fpg_core.floor_plan_scoring.evaluators.enclosed_voids import (
    EnclosedVoidsVisualizationData,
)
from fpg_core.types_new import FloorPlan
from matplotlib.figure import Figure
from matplotlib.patches import Polygon as PolygonPatch

from ....config import RenderConfig
from ....matplotlib_backend.renderer import create_figure
from .common import draw_floor_plan


def render_enclosed_voids_figure(
    floor_plan: FloorPlan,
    payload: EnclosedVoidsVisualizationData,
    *,
    config: RenderConfig,
) -> Figure:
    figure, axes = create_figure(config)
    draw_floor_plan(
        axes,
        floor_plan,
        "Floor Plan Scoring — Enclosed Voids",
    )
    for index, void in enumerate(payload.voids, start=1):
        color = "#dc2626" if void.affects_score else "#f59e0b"
        axes.add_patch(
            PolygonPatch(
                void.points,
                closed=True,
                facecolor=color,
                edgecolor="#7f1d1d" if void.affects_score else "#92400e",
                linewidth=1.7,
                alpha=0.72,
                zorder=20,
            )
        )
        center_x = sum(x for x, _ in void.points) / len(void.points)
        center_y = sum(y for _, y in void.points) / len(void.points)
        axes.text(
            center_x,
            center_y,
            f"Void {index}\narea={void.area:.2f}",
            ha="center",
            va="center",
            fontsize=8,
            weight="bold",
            color="#ffffff",
            zorder=25,
        )
    return figure

from __future__ import annotations

from matplotlib.axes import Axes
from matplotlib.patches import Polygon as PolygonPatch

from app.algorithms.types_new import FloorPlan


def draw_floor_plan(axes: Axes, floor_plan: FloorPlan, title: str) -> None:
    for room in floor_plan.rooms:
        points = [(float(point.x), float(point.y)) for point in room.boundary.points]
        axes.add_patch(
            PolygonPatch(
                points,
                closed=True,
                facecolor="#e2e8f0",
                edgecolor="#475569",
                linewidth=1.0,
                alpha=0.7,
                zorder=5,
            )
        )
        center_x = sum(x for x, _ in points) / len(points)
        center_y = sum(y for _, y in points) / len(points)
        axes.text(
            center_x,
            center_y,
            room.name,
            ha="center",
            va="center",
            fontsize=7,
            color="#111827",
            zorder=10,
        )

    boundary = [
        (float(point.x), float(point.y)) for point in floor_plan.boundary.points
    ]
    axes.add_patch(
        PolygonPatch(
            boundary,
            closed=True,
            fill=False,
            edgecolor="#111827",
            linewidth=2.2,
            zorder=30,
        )
    )
    xs = [x for x, _ in boundary]
    ys = [y for _, y in boundary]
    padding = max(max(xs) - min(xs), max(ys) - min(ys)) * 0.04
    if padding <= 0:
        padding = 1.0
    axes.set_xlim(min(xs) - padding, max(xs) + padding)
    axes.set_ylim(min(ys) - padding, max(ys) + padding)
    axes.set_aspect("equal", adjustable="box")
    axes.set_xlabel("X (project units)")
    axes.set_ylabel("Y (project units)")
    axes.grid(
        linestyle="--",
        linewidth=0.45,
        color="#94a3b8",
        alpha=0.45,
        zorder=0,
    )
    axes.set_title(title, fontsize=14, weight="bold", pad=14)

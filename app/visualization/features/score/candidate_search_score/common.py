from __future__ import annotations

from collections.abc import Iterable

from fpg_core.candidate_scoring.evaluators.common import EvaluationPoint
from matplotlib.axes import Axes


def draw_candidate_points(
    axes: Axes,
    points: Iterable[EvaluationPoint],
    *,
    colors: dict[str, str] | None = None,
) -> None:
    for point in points:
        color = colors.get(point.room_id, "#2563eb") if colors else "#2563eb"
        axes.scatter(
            point.x,
            point.y,
            s=72,
            color=color,
            edgecolors="#111827",
            linewidths=0.7,
            zorder=20,
        )
        axes.annotate(
            point.name,
            (point.x, point.y),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8,
            color="#111827",
            zorder=30,
        )


def configure_candidate_axes(
    axes: Axes,
    floor_width: float,
    floor_length: float,
    title: str,
) -> None:
    padding = max(floor_width, floor_length) * 0.04
    axes.set_xlim(-padding, floor_width + padding)
    axes.set_ylim(-padding, floor_length + padding)
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

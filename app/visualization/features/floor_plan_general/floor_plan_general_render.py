from __future__ import annotations

import math
from collections.abc import Sequence
from textwrap import wrap

from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import Polygon as PolygonPatch

from app.algorithms.types_new import (
    FloorPlanOpening,
    FloorPlanRoom,
    OpeningType,
    Point,
    RoomType,
)

from ...config import RenderConfig
from ...matplotlib_backend.renderer import create_figure_grid
from .models import FloorPlanFlowVisualization, FloorPlanVisualizationStage

_PROJECT_UNITS_PER_METRE = 10
_GRID_INTERVAL = 10
_MAX_COLUMNS = 3
_PANEL_WIDTH_INCHES = 6.0
_PANEL_HEIGHT_INCHES = 4.8

_ROOM_COLORS: dict[RoomType, str] = {
    RoomType.BEDROOM: "#dbeafe",
    RoomType.BATHROOM: "#cffafe",
    RoomType.ATTACHED_BATHROOM: "#a5f3fc",
    RoomType.LIVING_ROOM: "#fef3c7",
    RoomType.KITCHEN: "#fed7aa",
    RoomType.DINING_ROOM: "#fde68a",
    RoomType.HALLWAY: "#e5e7eb",
    RoomType.VERANDA: "#dcfce7",
    RoomType.GARAGE: "#d1d5db",
    RoomType.OPEN_AREA: "#f3f4f6",
}


def render_floor_plan_general_figure(
    payload: FloorPlanFlowVisualization,
    *,
    config: RenderConfig,
) -> Figure:
    """Render every stage into one ordered, combined flow figure."""
    total_stages = len(payload.stages)
    columns = min(_MAX_COLUMNS, total_stages)
    rows = math.ceil(total_stages / columns)

    figure_width = max(7.0, columns * _PANEL_WIDTH_INCHES)
    figure_height = rows * _PANEL_HEIGHT_INCHES + 0.7
    figure, axes_grid = create_figure_grid(
        config,
        rows=rows,
        columns=columns,
        width_inches=figure_width,
        height_inches=figure_height,
    )
    axes = tuple(axis for row in axes_grid for axis in row)

    for stage_index, stage in enumerate(payload.stages):
        _draw_stage(
            axes[stage_index],
            stage,
            stage_number=stage_index + 1,
            total_stages=total_stages,
        )

    for unused_axis in axes[total_stages:]:
        unused_axis.set_visible(False)

    figure.suptitle(
        f"Floor Plan Generation Flow — {total_stages} Stages",
        fontsize=18,
        weight="bold",
        y=0.992,
    )
    figure.subplots_adjust(
        left=0.045,
        right=0.985,
        bottom=0.055,
        top=0.91,
        wspace=0.22,
        hspace=0.48,
    )
    return figure


def _draw_stage(
    axes: Axes,
    stage: FloorPlanVisualizationStage,
    *,
    stage_number: int,
    total_stages: int,
) -> None:
    floor_plan = stage.floor_plan

    for room in floor_plan.rooms:
        _draw_room(axes, room)

    for opening in floor_plan.openings:
        _draw_opening(axes, opening)

    boundary_points = _xy_pairs(floor_plan.boundary.points)
    axes.add_patch(
        PolygonPatch(
            boundary_points,
            closed=True,
            fill=False,
            edgecolor="#111827",
            linewidth=2.4,
            zorder=30,
        )
    )

    min_x, max_x, min_y, max_y = _bounds(floor_plan.boundary.points)
    padding = max(max_x - min_x, max_y - min_y) * 0.045
    if padding <= 0:
        padding = 1.0

    axes.set_xlim(min_x - padding, max_x + padding)
    axes.set_ylim(min_y - padding, max_y + padding)
    axes.set_aspect("equal", adjustable="box")
    axes.set_xlabel("X (project units)", fontsize=8)
    axes.set_ylabel("Y (project units)", fontsize=8)
    axes.set_xticks(_grid_ticks(min_x, max_x))
    axes.set_yticks(_grid_ticks(min_y, max_y))
    axes.tick_params(axis="both", labelsize=7)
    axes.grid(
        linestyle="--",
        linewidth=0.45,
        color="#94a3b8",
        alpha=0.45,
        zorder=0,
    )

    axes.text(
        0.015,
        0.985,
        f"#{stage_number}",
        transform=axes.transAxes,
        ha="left",
        va="top",
        fontsize=14,
        weight="bold",
        color="#ffffff",
        zorder=50,
        bbox={
            "boxstyle": "round,pad=0.28",
            "facecolor": "#1d4ed8",
            "edgecolor": "#1e3a8a",
            "alpha": 0.96,
        },
    )

    floor_width = max_x - min_x
    floor_length = max_y - min_y
    profile_name = stage.profile_name or "-"
    title = (
        f"Stage {stage_number} / {total_stages} — {stage.stage_name}\n"
        f"ID: {_truncate(stage.stage_id, 30)}  |  "
        f"Category: {_truncate(stage.category, 22)}  |  "
        f"Profile: {_truncate(profile_name, 24)}\n"
        f"Rooms: {len(floor_plan.rooms)}  |  "
        f"Openings: {len(floor_plan.openings)}  |  "
        f"Floor: {_metres(floor_width)} × {_metres(floor_length)} m"
    )
    axes.set_title(title, fontsize=9.5, weight="semibold", pad=10, linespacing=1.35)


def _truncate(value: str, max_characters: int) -> str:
    if len(value) <= max_characters:
        return value
    return f"{value[: max_characters - 1]}…"


def _draw_room(axes: Axes, room: FloorPlanRoom) -> None:
    points = tuple(room.boundary.points)
    axes.add_patch(
        PolygonPatch(
            _xy_pairs(points),
            closed=True,
            facecolor=_ROOM_COLORS.get(room.room_type, "#f8fafc"),
            edgecolor="#334155",
            linewidth=1.1,
            alpha=0.88,
            zorder=10,
        )
    )

    center_x, center_y = _polygon_centroid(points)
    min_x, max_x, min_y, max_y = _bounds(points)
    width = max_x - min_x
    length = max_y - min_y
    room_name = "\n".join(wrap(room.name, width=14))
    label = f"{room_name}\n{_metres(width)} × {_metres(length)} m"
    rotation = 90.0 if length > width * 2.0 and width < 20 else 0.0
    axes.text(
        center_x,
        center_y,
        label,
        ha="center",
        va="center",
        fontsize=_room_font_size(width, length),
        color="#111827",
        weight="semibold",
        rotation=rotation,
        rotation_mode="anchor",
        zorder=20,
        clip_on=True,
    )


def _draw_opening(axes: Axes, opening: FloorPlanOpening) -> None:
    color = "#1d4ed8" if opening.opening_type is OpeningType.WINDOW else "#92400e"
    axes.plot(
        (opening.start.x, opening.end.x),
        (opening.start.y, opening.end.y),
        color=color,
        linewidth=3.0,
        solid_capstyle="round",
        zorder=25,
    )


def _xy_pairs(points: Sequence[Point]) -> list[tuple[float, float]]:
    return [(float(point.x), float(point.y)) for point in points]


def _bounds(points: Sequence[Point]) -> tuple[float, float, float, float]:
    xs = [float(point.x) for point in points]
    ys = [float(point.y) for point in points]
    return min(xs), max(xs), min(ys), max(ys)


def _polygon_centroid(points: Sequence[Point]) -> tuple[float, float]:
    coordinates = _xy_pairs(points)
    signed_area_twice = 0.0
    centroid_x = 0.0
    centroid_y = 0.0

    for index, (x1, y1) in enumerate(coordinates):
        x2, y2 = coordinates[(index + 1) % len(coordinates)]
        cross = x1 * y2 - x2 * y1
        signed_area_twice += cross
        centroid_x += (x1 + x2) * cross
        centroid_y += (y1 + y2) * cross

    if abs(signed_area_twice) < 1e-9:
        min_x, max_x, min_y, max_y = _bounds(points)
        return (min_x + max_x) / 2.0, (min_y + max_y) / 2.0

    scale = 3.0 * signed_area_twice
    return centroid_x / scale, centroid_y / scale


def _grid_ticks(minimum: float, maximum: float) -> list[int]:
    start = int(minimum // _GRID_INTERVAL) * _GRID_INTERVAL
    stop = int(maximum // _GRID_INTERVAL + 1) * _GRID_INTERVAL
    return list(range(start, stop + 1, _GRID_INTERVAL))


def _metres(project_units: float) -> str:
    return f"{project_units / _PROJECT_UNITS_PER_METRE:.1f}"


def _room_font_size(width: float, length: float) -> float:
    shortest_side = min(width, length)
    if shortest_side < 20:
        return 5.5
    if shortest_side < 30:
        return 6.5
    return 7.5

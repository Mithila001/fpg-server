from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.algorithms.types_new import (
    FloorPlan,
    FloorPlanRoom,
    OpeningType,
    Point,
    RoomRole,
)

from ..backend import RendererFactory
from ..config import GridStyle, RenderConfig
from ..geometry import Bounds, PointTuple, polygon_centroid
from ..matplotlib_backend import create_matplotlib_renderer

_ROOM_COLORS: dict[str, str] = {
    "bedroom": "#bfdbfe",
    "bathroom": "#a7f3d0",
    "attached_bathroom": "#6ee7b7",
    "living_room": "#fde68a",
    "kitchen": "#fdba74",
    "dining_room": "#fcd34d",
    "hallway": "#e5e7eb",
    "veranda": "#d9f99d",
    "garage": "#cbd5e1",
    "open_area": "#ddd6fe",
}


@dataclass(frozen=True, slots=True)
class FloorPlanRenderOptions:
    title: str | None = None
    show_grid: bool = True
    show_floor_boundary: bool = True
    show_room_fill: bool = True
    show_room_labels: bool = True
    show_room_ids: bool = False
    show_room_dimensions: bool = False
    show_openings: bool = True
    room_fill_alpha: float = 0.48
    room_line_width: float = 1.4
    floor_boundary_line_width: float = 2.3
    opening_line_width: float = 4.0


def render_floor_plan(
    floor_plan: FloorPlan,
    output_path: str | Path,
    *,
    options: FloorPlanRenderOptions | None = None,
    config: RenderConfig | None = None,
    grid_style: GridStyle | None = None,
    renderer_factory: RendererFactory = create_matplotlib_renderer,
) -> Path:
    selected_options = options or FloorPlanRenderOptions()
    selected_config = config or RenderConfig()
    selected_grid = grid_style or GridStyle()
    boundary_points = _polygon_points(floor_plan.boundary.points)
    world_bounds = Bounds.from_points(boundary_points).padded(selected_config.padding_units)

    renderer = renderer_factory(world_bounds, selected_config)
    try:
        if selected_options.show_grid:
            renderer.draw_grid(selected_grid)

        for room_index, room in enumerate(floor_plan.rooms):
            room_points = _polygon_points(room.boundary.points)
            room_type_value = _enum_value(room.room_type)
            room_color = _ROOM_COLORS.get(room_type_value, _fallback_color(room_index))
            is_placeholder = room.role == RoomRole.SOLVER_PLACEHOLDER

            renderer.draw_polygon(
                room_points,
                face_color=room_color if selected_options.show_room_fill else "none",
                edge_color="#334155",
                alpha=selected_options.room_fill_alpha if selected_options.show_room_fill else 1.0,
                line_width=selected_options.room_line_width,
                zorder=2.0,
                hatch="///" if is_placeholder else None,
            )

            if selected_options.show_room_labels:
                renderer.draw_text(
                    polygon_centroid(room_points),
                    _room_label(room, room_points, selected_options),
                    color="#0f172a",
                    font_size=8.5,
                    background_color="#ffffff",
                    zorder=6.0,
                )

        if selected_options.show_floor_boundary:
            closed_boundary = [*boundary_points, boundary_points[0]]
            renderer.draw_polyline(
                closed_boundary,
                color="#020617",
                line_width=selected_options.floor_boundary_line_width,
                zorder=5.0,
            )

        if selected_options.show_openings:
            for opening in floor_plan.openings:
                opening_color = (
                    "#dc2626"
                    if opening.opening_type == OpeningType.DOOR
                    else "#0284c7"
                )
                renderer.draw_polyline(
                    [
                        (opening.start.x, opening.start.y),
                        (opening.end.x, opening.end.y),
                    ],
                    color=opening_color,
                    line_width=selected_options.opening_line_width,
                    zorder=7.0,
                )

        if selected_options.title:
            renderer.set_title(selected_options.title)
        return renderer.save(Path(output_path))
    finally:
        renderer.close()


def _polygon_points(points: tuple[Point, ...]) -> list[PointTuple]:
    converted = [(float(point.x), float(point.y)) for point in points]
    if len(converted) < 3:
        raise ValueError("floor-plan polygons require at least three points")
    return converted


def _room_label(
    room: FloorPlanRoom,
    points: list[PointTuple],
    options: FloorPlanRenderOptions,
) -> str:
    parts = [str(room.name)]
    if options.show_room_ids:
        parts.append(str(room.id))
    if options.show_room_dimensions:
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        parts.append(f"{max(xs) - min(xs):g} × {max(ys) - min(ys):g} units")
    return "\n".join(parts)


def _enum_value(value: object) -> str:
    raw_value = getattr(value, "value", value)
    return str(raw_value)


def _fallback_color(index: int) -> str:
    palette = ("#fecaca", "#ddd6fe", "#bae6fd", "#bbf7d0", "#fed7aa")
    return palette[index % len(palette)]

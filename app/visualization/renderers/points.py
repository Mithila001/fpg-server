from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from ..backend import RendererFactory
from ..config import GridStyle, RenderConfig
from ..geometry import Bounds, PointTuple
from ..matplotlib_backend import create_matplotlib_renderer
from ..models import PathOverlay, PointMarker, ZoneOverlay
from .common import draw_markers, draw_paths, draw_zones


@dataclass(frozen=True, slots=True)
class PointMapRenderOptions:
    title: str | None = None
    show_grid: bool = True
    grid_on_top: bool = False
    show_labels: bool = True
    show_values: bool = False


def render_point_map(
    markers: Sequence[PointMarker],
    output_path: str | Path,
    *,
    zones: Sequence[ZoneOverlay] = (),
    paths: Sequence[PathOverlay] = (),
    bounds: Bounds | None = None,
    options: PointMapRenderOptions | None = None,
    config: RenderConfig | None = None,
    grid_style: GridStyle | None = None,
    renderer_factory: RendererFactory = create_matplotlib_renderer,
) -> Path:
    selected_options = options or PointMapRenderOptions()
    selected_config = config or RenderConfig()
    selected_grid = grid_style or GridStyle()
    world_bounds = bounds or _derive_bounds(markers, zones, paths)
    world_bounds = world_bounds.padded(selected_config.padding_units)

    renderer = renderer_factory(world_bounds, selected_config)
    try:
        if selected_options.show_grid and not selected_options.grid_on_top:
            renderer.draw_grid(selected_grid)

        draw_zones(renderer, zones)
        draw_paths(renderer, paths)
        draw_markers(
            renderer,
            markers,
            show_labels=selected_options.show_labels,
            show_values=selected_options.show_values,
        )

        if selected_options.show_grid and selected_options.grid_on_top:
            overlay_grid = GridStyle(
                visible=selected_grid.visible,
                minor_step=selected_grid.minor_step,
                major_step=selected_grid.major_step,
                minor_color=selected_grid.minor_color,
                major_color=selected_grid.major_color,
                minor_line_width=selected_grid.minor_line_width,
                major_line_width=selected_grid.major_line_width,
                minor_alpha=selected_grid.minor_alpha,
                major_alpha=selected_grid.major_alpha,
                zorder=5.0,
            )
            renderer.draw_grid(overlay_grid)

        if selected_options.title:
            renderer.set_title(selected_options.title)
        return renderer.save(Path(output_path))
    finally:
        renderer.close()


def _derive_bounds(
    markers: Sequence[PointMarker],
    zones: Sequence[ZoneOverlay],
    paths: Sequence[PathOverlay],
) -> Bounds:
    points: list[PointTuple] = [marker.point for marker in markers]
    for zone in zones:
        points.extend(zone.points)
    for path in paths:
        points.extend(path.points)

    if not points:
        raise ValueError("point map needs markers, zones, paths, or explicit bounds")
    return Bounds.from_points(points)

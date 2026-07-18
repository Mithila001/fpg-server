from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from numpy.typing import ArrayLike

from ..backend import RendererFactory
from ..config import GridStyle, RenderConfig
from ..geometry import Bounds
from ..matplotlib_backend import create_matplotlib_renderer
from ..models import PathOverlay, PointMarker, ZoneOverlay
from .common import draw_markers, draw_paths, draw_zones


@dataclass(frozen=True, slots=True)
class HeatmapRenderOptions:
    title: str | None = None
    color_map: str = "viridis"
    interpolation: str = "nearest"
    alpha: float = 0.9
    minimum_value: float | None = None
    maximum_value: float | None = None
    show_grid: bool = True
    grid_on_top: bool = True
    show_colorbar: bool = True
    colorbar_label: str | None = None
    show_marker_labels: bool = True
    show_marker_values: bool = False


def render_heatmap(
    values: ArrayLike,
    extent: Bounds,
    output_path: str | Path,
    *,
    markers: Sequence[PointMarker] = (),
    zones: Sequence[ZoneOverlay] = (),
    paths: Sequence[PathOverlay] = (),
    options: HeatmapRenderOptions | None = None,
    config: RenderConfig | None = None,
    grid_style: GridStyle | None = None,
    renderer_factory: RendererFactory = create_matplotlib_renderer,
) -> Path:
    selected_options = options or HeatmapRenderOptions()
    selected_config = config or RenderConfig()
    selected_grid = grid_style or GridStyle()
    world_bounds = extent.padded(selected_config.padding_units)

    renderer = renderer_factory(world_bounds, selected_config)
    try:
        if selected_options.show_grid and not selected_options.grid_on_top:
            renderer.draw_grid(selected_grid)

        heatmap = renderer.draw_heatmap(
            values,
            extent,
            color_map=selected_options.color_map,
            alpha=selected_options.alpha,
            interpolation=selected_options.interpolation,
            minimum_value=selected_options.minimum_value,
            maximum_value=selected_options.maximum_value,
            zorder=0.5,
        )

        draw_zones(renderer, zones)
        draw_paths(renderer, paths)
        draw_markers(
            renderer,
            markers,
            show_labels=selected_options.show_marker_labels,
            show_values=selected_options.show_marker_values,
        )

        if selected_options.show_grid and selected_options.grid_on_top:
            renderer.draw_grid(
                GridStyle(
                    visible=selected_grid.visible,
                    minor_step=selected_grid.minor_step,
                    major_step=selected_grid.major_step,
                    minor_color=selected_grid.minor_color,
                    major_color=selected_grid.major_color,
                    minor_line_width=selected_grid.minor_line_width,
                    major_line_width=selected_grid.major_line_width,
                    minor_alpha=0.45,
                    major_alpha=0.75,
                    zorder=5.0,
                )
            )

        if selected_options.show_colorbar:
            renderer.add_colorbar(heatmap, label=selected_options.colorbar_label)
        if selected_options.title:
            renderer.set_title(selected_options.title)
        return renderer.save(Path(output_path))
    finally:
        renderer.close()

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from numpy.typing import ArrayLike

from app.algorithms.types_new import FloorPlan

from .config import GridStyle, RenderConfig
from .geometry import Bounds
from .models import GraphEdge, GraphNode, PathOverlay, PointMarker, ZoneOverlay
from .output import VisualizationOutputManager
from .renderers import (
    FloorPlanRenderOptions,
    GraphRenderOptions,
    HeatmapRenderOptions,
    PointMapRenderOptions,
)
from .renderers import render_floor_plan as render_floor_plan_image
from .renderers import render_graph as render_graph_image
from .renderers import render_heatmap as render_heatmap_image
from .renderers import render_point_map as render_point_map_image


@dataclass(slots=True)
class VisualizationService:
    """Server-facing facade for path creation and image rendering."""

    output_manager: VisualizationOutputManager
    render_config: RenderConfig = field(default_factory=RenderConfig)
    grid_style: GridStyle = field(default_factory=GridStyle)

    def render_floor_plan(
        self,
        floor_plan: FloorPlan,
        *,
        stage: str,
        name: str,
        job_id: str | None = None,
        options: FloorPlanRenderOptions | None = None,
    ) -> Path:
        output_path = self.output_manager.build_path(
            stage=stage,
            name=name,
            job_id=job_id,
        )
        return render_floor_plan_image(
            floor_plan,
            output_path,
            options=options,
            config=self.render_config,
            grid_style=self.grid_style,
        )

    def render_point_map(
        self,
        markers: Sequence[PointMarker],
        *,
        stage: str,
        name: str,
        job_id: str | None = None,
        zones: Sequence[ZoneOverlay] = (),
        paths: Sequence[PathOverlay] = (),
        bounds: Bounds | None = None,
        options: PointMapRenderOptions | None = None,
    ) -> Path:
        output_path = self.output_manager.build_path(
            stage=stage,
            name=name,
            job_id=job_id,
        )
        return render_point_map_image(
            markers,
            output_path,
            zones=zones,
            paths=paths,
            bounds=bounds,
            options=options,
            config=self.render_config,
            grid_style=self.grid_style,
        )

    def render_graph(
        self,
        nodes: Sequence[GraphNode],
        edges: Sequence[GraphEdge],
        *,
        stage: str,
        name: str,
        job_id: str | None = None,
        bounds: Bounds | None = None,
        options: GraphRenderOptions | None = None,
    ) -> Path:
        output_path = self.output_manager.build_path(
            stage=stage,
            name=name,
            job_id=job_id,
        )
        return render_graph_image(
            nodes,
            edges,
            output_path,
            bounds=bounds,
            options=options,
            config=self.render_config,
            grid_style=self.grid_style,
        )

    def render_heatmap(
        self,
        values: ArrayLike,
        extent: Bounds,
        *,
        stage: str,
        name: str,
        job_id: str | None = None,
        markers: Sequence[PointMarker] = (),
        zones: Sequence[ZoneOverlay] = (),
        paths: Sequence[PathOverlay] = (),
        options: HeatmapRenderOptions | None = None,
    ) -> Path:
        output_path = self.output_manager.build_path(
            stage=stage,
            name=name,
            job_id=job_id,
        )
        return render_heatmap_image(
            values,
            extent,
            output_path,
            markers=markers,
            zones=zones,
            paths=paths,
            options=options,
            config=self.render_config,
            grid_style=self.grid_style,
        )


def create_default_visualization_service(
    base_directory: str | Path | None = None,
) -> VisualizationService:
    output_manager = (
        VisualizationOutputManager(Path(base_directory))
        if base_directory is not None
        else VisualizationOutputManager.from_environment()
    )
    return VisualizationService(output_manager=output_manager)

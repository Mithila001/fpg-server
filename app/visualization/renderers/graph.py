from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from ..backend import RendererFactory
from ..config import GridStyle, RenderConfig
from ..geometry import Bounds, midpoint
from ..matplotlib_backend import create_matplotlib_renderer
from ..models import GraphEdge, GraphNode


@dataclass(frozen=True, slots=True)
class GraphRenderOptions:
    title: str | None = None
    show_grid: bool = True
    show_node_ids: bool = False
    show_node_values: bool = False
    show_edge_labels: bool = True
    node_radius_units: float | None = None


def render_graph(
    nodes: Sequence[GraphNode],
    edges: Sequence[GraphEdge],
    output_path: str | Path,
    *,
    bounds: Bounds | None = None,
    options: GraphRenderOptions | None = None,
    config: RenderConfig | None = None,
    grid_style: GridStyle | None = None,
    renderer_factory: RendererFactory = create_matplotlib_renderer,
) -> Path:
    if not nodes:
        raise ValueError("graph rendering requires at least one node")

    selected_options = options or GraphRenderOptions()
    selected_config = config or RenderConfig()
    selected_grid = grid_style or GridStyle()
    node_by_id = {node.id: node for node in nodes}
    if len(node_by_id) != len(nodes):
        raise ValueError("graph node IDs must be unique")

    _validate_edges(edges, node_by_id)
    world_bounds = bounds or Bounds.from_points(node.point for node in nodes)
    world_bounds = world_bounds.padded(selected_config.padding_units)
    default_radius = selected_options.node_radius_units or max(
        min(world_bounds.width, world_bounds.height) * 0.025,
        1.0,
    )

    renderer = renderer_factory(world_bounds, selected_config)
    try:
        if selected_options.show_grid:
            renderer.draw_grid(selected_grid)

        for edge in edges:
            source = node_by_id[edge.source_id]
            target = node_by_id[edge.target_id]
            edge_color = edge.color or ("#dc2626" if edge.highlighted else "#64748b")
            line_width = edge.line_width or (2.8 if edge.highlighted else 1.4)

            if edge.directed:
                renderer.draw_arrow(
                    source.point,
                    target.point,
                    color=edge_color,
                    line_width=line_width,
                    zorder=2.5,
                )
            else:
                renderer.draw_polyline(
                    [source.point, target.point],
                    color=edge_color,
                    line_width=line_width,
                    zorder=2.5,
                )

            if selected_options.show_edge_labels and edge.label:
                renderer.draw_text(
                    midpoint(source.point, target.point),
                    edge.label,
                    color=edge_color,
                    font_size=8.0,
                    background_color="#ffffff",
                    zorder=6.0,
                )

        for node in nodes:
            radius = node.radius_units or default_radius
            node_color = node.color or "#38bdf8"
            renderer.draw_circle(
                node.point,
                radius,
                face_color=node_color,
                edge_color="#0f172a",
                alpha=0.95,
                line_width=1.0,
                zorder=4.0,
            )

            label_parts: list[str] = []
            if node.label:
                label_parts.append(node.label)
            elif selected_options.show_node_ids:
                label_parts.append(node.id)
            if selected_options.show_node_values and node.value is not None:
                label_parts.append(f"{node.value:.2f}")

            if label_parts:
                renderer.draw_text(
                    node.point,
                    "\n".join(label_parts),
                    color="#0f172a",
                    font_size=8.0,
                    zorder=6.0,
                )

        if selected_options.title:
            renderer.set_title(selected_options.title)
        return renderer.save(Path(output_path))
    finally:
        renderer.close()


def _validate_edges(
    edges: Sequence[GraphEdge],
    node_by_id: dict[str, GraphNode],
) -> None:
    for edge in edges:
        if edge.source_id not in node_by_id:
            raise ValueError(f"edge source node does not exist: {edge.source_id}")
        if edge.target_id not in node_by_id:
            raise ValueError(f"edge target node does not exist: {edge.target_id}")

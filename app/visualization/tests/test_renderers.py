from __future__ import annotations

import numpy as np

from ..config import RenderConfig
from ..geometry import Bounds
from ..matplotlib_backend import MatplotlibRenderer
from ..renderers import (
    FloorPlanRenderOptions,
    GraphRenderOptions,
    HeatmapRenderOptions,
    PointMapRenderOptions,
    render_floor_plan,
    render_graph,
    render_heatmap,
    render_point_map,
)
from .builders import build_floor_plan, build_graph_data, build_point_map_data


def _assert_png_created(path) -> None:
    assert path.is_file()
    assert path.stat().st_size > 1_000
    assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_floor_plan_renderer_creates_png(tmp_path) -> None:
    output = render_floor_plan(
        build_floor_plan(),
        tmp_path / "floor-plan.png",
        options=FloorPlanRenderOptions(show_room_dimensions=True),
        config=RenderConfig(width_inches=6, height_inches=5, dpi=100),
    )
    _assert_png_created(output)


def test_point_map_renderer_creates_png(tmp_path) -> None:
    markers, zones, paths = build_point_map_data()
    output = render_point_map(
        markers,
        tmp_path / "points.png",
        zones=zones,
        paths=paths,
        options=PointMapRenderOptions(show_values=True),
    )
    _assert_png_created(output)


def test_graph_renderer_creates_png(tmp_path) -> None:
    nodes, edges = build_graph_data()
    output = render_graph(
        nodes,
        edges,
        tmp_path / "graph.png",
        options=GraphRenderOptions(show_node_values=True),
    )
    _assert_png_created(output)


def test_heatmap_renderer_creates_png(tmp_path) -> None:
    markers, zones, paths = build_point_map_data()
    values = np.arange(80, dtype=float).reshape(8, 10)
    output = render_heatmap(
        values,
        Bounds(0, 0, 100, 80),
        tmp_path / "heatmap.png",
        markers=markers,
        zones=zones,
        paths=paths,
        options=HeatmapRenderOptions(colorbar_label="Score"),
    )
    _assert_png_created(output)


def test_low_level_renderer_supports_arcs_and_curves(tmp_path) -> None:
    renderer = MatplotlibRenderer(
        Bounds(0, 0, 100, 80),
        RenderConfig(width_inches=5, height_inches=4, dpi=100),
    )
    try:
        renderer.draw_arc(
            (25, 25),
            20,
            20,
            0,
            90,
            color="#dc2626",
        )
        renderer.draw_quadratic_curve(
            (10, 60),
            (50, 75),
            (90, 60),
            color="#2563eb",
        )
        output = renderer.save(tmp_path / "curves.png")
    finally:
        renderer.close()

    _assert_png_created(output)

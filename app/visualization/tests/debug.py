from __future__ import annotations

import numpy as np

from ..api import create_default_visualization_service
from ..geometry import Bounds
from ..renderers import (
    FloorPlanRenderOptions,
    GraphRenderOptions,
    HeatmapRenderOptions,
    PointMapRenderOptions,
)
from .builders import build_floor_plan, build_graph_data, build_point_map_data


def main() -> None:
    service = create_default_visualization_service("var/visualizations")
    markers, zones, paths = build_point_map_data()
    nodes, edges = build_graph_data()

    outputs = [
        service.render_floor_plan(
            build_floor_plan(),
            job_id="debug-job",
            stage="solver",
            name="floor-plan",
            options=FloorPlanRenderOptions(
                title="Generated Floor Plan",
                show_room_dimensions=True,
            ),
        ),
        service.render_point_map(
            markers,
            zones=zones,
            paths=paths,
            bounds=Bounds(0, 0, 100, 80),
            job_id="debug-job",
            stage="candidate-search",
            name="trial-points",
            options=PointMapRenderOptions(
                title="Candidate Search Trial",
                show_values=True,
            ),
        ),
        service.render_graph(
            nodes,
            edges,
            bounds=Bounds(0, 0, 100, 80),
            job_id="debug-job",
            stage="candidate-scoring",
            name="adjacency-graph",
            options=GraphRenderOptions(
                title="Adjacency Scoring Graph",
                show_node_values=True,
            ),
        ),
        service.render_heatmap(
            np.arange(80, dtype=float).reshape(8, 10),
            Bounds(0, 0, 100, 80),
            markers=markers,
            paths=paths,
            job_id="debug-job",
            stage="candidate-scoring",
            name="zone-heatmap",
            options=HeatmapRenderOptions(
                title="Candidate Zone Heatmap",
                colorbar_label="Score",
            ),
        ),
    ]

    for output in outputs:
        print(output.resolve())


if __name__ == "__main__":
    main()

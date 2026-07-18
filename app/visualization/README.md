# Server-side Visualization

This package creates headless image files for candidate search, scoring, solver, post-processing, opening generation, and final floor-plan output.

## Location

```text
app/visualization/
```

Generated files should not be stored inside `app/`. The default runtime location is:

```text
var/visualizations/<job-id>/<stage>/<name>.png
```

Override it with the `FPG_VISUALIZATION_DIR` environment variable or pass a directory to `create_default_visualization_service()`.

## Structure

```text
app/visualization/
├── api.py                    # server-facing VisualizationService
├── backend.py                # backend protocol
├── config.py                 # image and grid configuration
├── geometry.py               # bounds and geometry helpers
├── models.py                 # point, zone, path, and graph DTOs
├── output.py                 # runtime output path management
├── matplotlib_backend/
│   └── renderer.py           # headless Matplotlib drawing engine
├── renderers/
│   ├── floor_plan.py         # FloorPlan rendering
│   ├── points.py             # Optuna/candidate point maps
│   ├── graph.py              # scoring graph visualization
│   ├── heatmap.py            # heatmaps with overlays
│   └── common.py             # shared overlay composition
└── tests/
```

## Install

```bash
pip install matplotlib numpy pytest
```

Matplotlib is used without `pyplot`; every render owns a separate `FigureCanvasAgg`, which is appropriate for headless server image export.

## Basic server usage

```python
from app.visualization import create_default_visualization_service

visualization = create_default_visualization_service()

path = visualization.render_floor_plan(
    floor_plan,
    job_id=job_id,
    stage="solver",
    name="initial-layout",
)
```

Candidate points, zones, graph nodes, paths, and heatmaps use the same service through `render_point_map()`, `render_graph()`, and `render_heatmap()`.

## Unique visualizations

A specialized algorithm visualization can use `MatplotlibRenderer` directly. It supports polygons, lines, segments, circles, labels, arrows, arcs, quadratic curves, points, grids, and heatmaps. Keep the algorithm-specific composition in the owning algorithm package, but reuse this package for drawing and output management.

## Run tests

From the project root:

```bash
python -m pytest app/visualization/tests -sv
```

## Generate sample images

```bash
python -m app.visualization.tests.debug
```

The sample images will be written under `var/visualizations/debug-job/`.

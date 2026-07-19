# Visualization

`app/visualization` is a small, developer-oriented package for inspecting algorithm behavior, intermediate pipeline data, and explicitly producing server-side PNG artifacts. It is not a general graphics framework, reusable UI system, renderer registry, or plugin architecture.

## Design

Visualization code is feature-owned. A feature owns its models, geometry, Matplotlib calls, labels, colors, layout, axes, and layer order. There is deliberately no shared primitive or reusable-component layer: modest duplication is safer than coupling unrelated visualizations before stable reuse exists.

The initial package contains only Candidate Search:

```text
app/visualization/
├── api.py                         supported public boundary
├── config.py                      package-wide figure/export defaults
├── output_manager.py              safe PNG paths, saving, and cleanup
├── matplotlib_backend/            headless figure lifecycle only
├── features/candidate_search/     models and complete drawing behavior
├── playground/candidate_search/   realistic manual runner and JSON data
└── output/                         ignored generated PNG artifacts
```

The dependency direction is application code → `api.py` → feature renderer → Matplotlib/backend. Separately, `api.py` delegates persistence to `output_manager.py` → PNG. The backend never imports features; features do not import one another; the output manager contains no drawing; algorithms do not accept Matplotlib objects; and production code never imports playground modules.

## Public API

Outside code uses only:

```python
from app.visualization.api import (
    CandidatePoint,
    CandidateSearchVisualization,
    SearchBounds,
    render_candidate_search,
)
```

The root package intentionally re-exports this function and its three input model types. Feature modules, the backend, and the output manager are private implementation details. Rendering is explicit: importing the package creates no figures, directories, or files.

`config.py` holds only universal image size, DPI, background, transparency, export bounding-box, and output-root defaults. Candidate Search appearance and geometry remain in its feature folder.

## Candidate Search output

The API creates sortable, collision-resistant PNG names beneath the managed root:

```text
output/candidate_search/<optional-run-id>/
  20260719-214530-123456_trial-17_a1b2c3d4.png
```

All path components are sanitized. The output manager creates directories, saves the PNG, and closes the figure even if saving fails. Feature renderers never choose paths or call `savefig()` in the official flow.

Project coordinates use integer units where **10 units = 1 metre**.

## Playground

From the repository root, run:

```bash
python -m app.visualization.playground.candidate_search.run
```

It loads realistic adjacent JSON, constructs the Candidate Search view model, calls the public API, and prints the generated path. This is development-only manual validation, not production code.

## Adding a feature

Create `features/<feature_name>/models.py` and `<feature_name>_render.py`; keep its complete appearance and geometry there. Add feature-local `styles.py`, `layers.py`, or helpers only when complexity warrants them. Then add one explicit API function, a matching JSON-backed playground runner, managed PNG persistence, and update this README. Do not introduce a generic dispatcher or shared component merely because two features look somewhat similar.

The previous generic renderers, overlay/domain contracts, mock runner, and visualization test suite were intentionally removed in this complete redesign.

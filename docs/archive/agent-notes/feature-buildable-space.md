# Agent Notes: Feature - Buildable Space and Land Processing

## 1. API endpoint and rate limiting
- `app/routes/buildable_space_route.py` exposes `POST /algorithms/buildable-space` with payload model:
  - `area`, `segmentsCoordinates`, `roadConnected`, `min_width`, `min_height`, `should_plot`
- Uses same per-client throttling pattern as format endpoints (`_last_buildable_space_request`).
- Input is converted via `app.util.unit_converter.converter_cm_to_unit` to solver internal units, and response conversion back with `converter_unit_to_meters`.

## 2. Service orchestration
- `app/services/buildable_space_manager.py` handles pipeline logic:
  - validates land boundary and TA line with `_extract_polygon_coordinates`, `_extract_ta_line`.
  - finds usable land boundary via `find_usable_land_space`.
  - search for largest axis-aligned rectangle via `FPBoundaryFinder.fp_boundary_finder`.
  - returns payload with `status`, `message`, `buildable_rectangle`, `shrunk_boundary`, `metadata`.

## 3. Geometric algorithm modules
- `app/algorithms/usable_land_space_finder`: convex polygon classification and offset shrink.
  - `classify_segments_and_offsets` (direction and road-aware offsets).
  - `shrink_convex_polygon` + convexity enforcement and area checks.
- `app/algorithms/fp_boundary_finder`: sweep-line largest rectangle inside polygon using coordinate transform and rotation.
  - supports parallel and perpendicular rectangle options.
  - includes polygon transform utilities in `util_fp_bf`.

## 4. Error handling and plotting
- Known error conditions handled in manager: insufficient vertices, invalid TA line, impossible rectangle.
- Setup for debug plots in `plot_buildable_space` writes PNGs under `test/dev/land_boundary_output` when `should_plot` is true.
- Logs success/fail events with `SystemLogger` for observability.

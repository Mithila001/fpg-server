# Agent Notes: Project Patterns

## 1. Architectural Layers
- HTTP Layer: `app/main.py`, `app/routes/routes.py`.
  - Exposes `/algorithms/format` and `/algorithms/format/v2` endpoints.
  - Handles rate limiting, request logging, and unit conversion.
- Service Layer: `app/services/algorithm_manager.py`, `app/services/algorithm_manager_v2.py`.
  - `algorithm_manager.py`: DB template-driven solver flow.
  - `algorithm_manager_v2.py`: payload-driven API flow (validates template + constraints before solve).
  - Both produce normalized geometry and API payload with walls and rooms.
- Algorithm Layer: `app/algorithms/fpg_rooms`, `app/algorithms/fpg_opening`, `app/algorithms/fp_boundary_finder`, `app/algorithms/usable_land_space_finder`.
  - Floor plan generation (`FloorPlanGenerator`).
  - Optuna optimization (`fpg_optuna`).
  - Buildable land rectangle selection (`FPBoundaryFinder`).
  - Usable land boundary shrinking (`find_usable_land_space`).
  - Post-processing into walls/openings (`fpg_post_process`, `fpg_score`).

## 2. Data Sources and Normalization
- DB access via SQLModel in `app/core/database.py` and `app/crud` objects.
- Preprocessing in `app/util/room_requirements.py` and `app/util/dev_use_mock_db.py`.
- Default settings from `app/core/fpg_rooms/config_fpg.py`.
- Template constraints in `app/models` and `app/schemas/db`.

## 3. Processing Pipeline
1. Load room templates + constraints (DB or mock JSON fallback).
2. Build `RoomData` + `FpgRequirements` objects.
3. Run solver (`FloorPlanGenerator.generate()`), optionally with Optuna.
4. Post-process raw solution (walls union, compact by room).
5. Generate openings (`fpg_opening.generate_openings`).
6. Final payload: `{status, message, walls, compact_by_room}`.

## 4. Error Handling / Validation
- V1 pipeline has minimal pre-validation and uses fallback data with `should_bypass` flags.
- V2 pipeline includes `pre_validation` for floor area constraints and ensures room constraints exist.
- Both pipelines catch exceptions and return structured error payloads.

## 5. Logging / Tracking
- System tracking with `app.util.logger.SystemLogger` on pipeline stages.
- Request/response logging through `app.util.logger.fpg_rooms.api_logger.ApiLogger` middleware.
- Optuna summaries printed in console and tracked in logger.

## 6. Test and Dev Utilities
- Plotting in `test/dev`: grid snapping, floor plan output, and refine-stage visualizations.
- `app/routes/routes.py` references `plot_floor_plan_payload` for optional endpoint data inspections.

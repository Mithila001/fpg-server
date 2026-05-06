# Floor Plan Generator Optuna Guide

This module runs Optuna-based hyperparameter optimization on top of the existing
floor-plan generator and scoring pipeline.

## What gets optimized in v1

- `config.min_coverage`
- Per-room dimension bounds:
  - `min_w`, `min_h`
  - `max_w`, `max_h`

The objective is to maximize `score_report.total_score`.

## Sampling policy

Optuna now uses simple, uniform coordinate sampling for all rooms and hallways.

What is enforced during sampling:

- Boundary/radius limits
  - Each sampled point stays inside `[radius, floor_size - radius]` for both axes.
- Grid snapping
  - Search bounds are snapped to `OPTUNA_SEARCH_SPACE_GRID_SCALE`.
  - `suggest_float(..., step=OPTUNA_SEARCH_SPACE_GRID_SCALE)` keeps samples on the same grid.

What is intentionally removed:

- Room-aware sampler narrowing (front/private/back/proximity policies).
- Optuna-level duplicate-coordinate rejection.

This keeps Optuna focused on broad point exploration while the scoring + solver
pipeline drives quality and final adjustment.

## Integration points

- `app/services/algorithm_manager.py`
  - `DEV_RUN(use_optuna=True, n_trials=50)`
  - `RunFPG(requirements, verbose=True)`
  - `OptunaEntry(requirements, n_trials=50, ...)`
- `app/algorithms/fpg_rooms/fpg_optuna/runner.py`
  - `run_optuna_optimization(...)`

## Quick start

1. Ensure your database has room templates, room size constraints, and relation constraints.
2. Run DEV mode with Optuna enabled (default):

```bash
python -c "from app.services.algorithm_manager import DEV_RUN; DEV_RUN()"
```

3. Run one-shot baseline (without Optuna):

```bash
python -c "from app.services.algorithm_manager import DEV_RUN; DEV_RUN(use_optuna=False)"
```

4. Run with custom trials:

```bash
python -c "from app.services.algorithm_manager import DEV_RUN; DEV_RUN(use_optuna=True, n_trials=50)"
```

## Study storage and dashboard

By default, `OptunaEntry` stores trials in:

`sqlite:///optuna_fpg.db`

Launch dashboard:

```bash
optuna-dashboard sqlite:///optuna_fpg.db
```

## Failure handling

- Precheck rejects malformed requirement trials before solver call.
- Unsolved, invalid, or infeasible trials return objective score `0.0`.
- Trial metadata captures status and reason for easier debugging.

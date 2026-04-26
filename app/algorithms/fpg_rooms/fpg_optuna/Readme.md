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

Optuna now uses a room-aware sampling layer in
`app/algorithms/fpg_rooms/fpg_optuna/sampling_logic/` so positions are filtered
before graph scoring and solver execution.

Current placement rules:

- `veranda` and `garage`
  - Hard front anchoring near `y = 0` using the room radius as the front-band limit.
- `livingRoom`
  - Biased toward `veranda` using a center-y proximity band.
- `diningRoom` and `kitchen`
  - Sampled with a proximity band so they stay relatively close to each other.
  - `kitchen` still remains back-biased and avoids the front band.
- `bathroom`
  - Back-biased and prevented from sampling near the front side.

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

# Floor Plan Solver Tests

These tests execute the real OR-Tools CP-SAT solver. They do not mock the
solver, model builder, constraints, profiles, preparation, extraction, or
refinement flow.

## Measurement contract

- `10` project units = `1` meter.
- `1` project unit = `10` centimeters.
- Input dimensions use whole project units.

The realistic test house is `120 x 110` units, which represents `12 m x 11 m`.

## Run automated tests

```bash
pytest app/algorithms/floor_plan_solver/tests -q
```

## Run the JSON debug pipeline

Use exact built-in profile time limits:

```bash
python -m app.algorithms.floor_plan_solver.tests.debug
```

Use a shorter manual per-stage time limit:

```bash
python -m app.algorithms.floor_plan_solver.tests.debug --max-time-seconds 5
```

Generated files are JSON only and are written to `tests/output/`:

```text
initial_generation.json
refinement_a.json
refinement_b.json
```

# Candidate Search

A lightweight Optuna-based coordinate optimizer.

This module **does not know anything about floor plans, rooms, hallways, or scoring logic.** Its only responsibility is to search for the best `(x, y)` coordinates for a set of labelled targets.

---

## Usage

```python
from app.algorithms.candidate_search import (
    CoordinateTarget,
    CoordinateOptimizationSettings,
    optimize_coordinates,
)

targets = [
    CoordinateTarget(label="living_room"),
    CoordinateTarget(label="kitchen"),
    CoordinateTarget(label="bedroom_1"),
]

settings = CoordinateOptimizationSettings(
    min_x=0,
    max_x=100,
    min_y=0,
    max_y=80,
    grid_resolution=5,
    trial_count=100,
)

def scorer(coordinates):
    # Return a higher score for better layouts
    return calculate_score(coordinates)

result = optimize_coordinates(
    targets=targets,
    settings=settings,
    evaluator=scorer,
)
```

---

## Inputs

### CoordinateTarget

Defines a point that Optuna should generate.

```python
CoordinateTarget(
    label="living_room"
)
```

- Labels must be unique.
- The label is returned unchanged in the final result.

---

### CoordinateOptimizationSettings

Controls the search space.

| Field             | Description                                    |
| ----------------- | ---------------------------------------------- |
| `min_x`           | Minimum X coordinate                           |
| `max_x`           | Maximum X coordinate                           |
| `min_y`           | Minimum Y coordinate                           |
| `max_y`           | Maximum Y coordinate                           |
| `grid_resolution` | Coordinate step size (e.g. `5` → `0,5,10,...`) |
| `trial_count`     | Number of Optuna trials                        |

---

### Evaluator

The evaluator receives generated coordinates and returns a numeric score.

```python
def evaluator(coordinates) -> float:
    ...
```

Higher scores are considered better.

The evaluator is responsible for interpreting what the coordinates mean.

---

## Output

```python
result.score
result.coordinates
```

Example:

```python
for point in result.coordinates:
    print(point.label, point.x, point.y)
```

---

## Responsibilities

This module **does**:

- Generate coordinates
- Search using Optuna
- Respect grid resolution
- Return the best coordinate set

This module **does not**:

- Generate floor plans
- Run CP-SAT
- Calculate layout scores
- Validate architectural rules
- Know what the labels represent

Those responsibilities belong to the caller.

---

## Design Goal

Keep the optimizer generic.

```
Labels
    +
Search Settings
    +
Scoring Function
        ↓
Candidate Search
        ↓
Best Coordinates
```

This separation keeps the module easy to understand, test, and reuse.

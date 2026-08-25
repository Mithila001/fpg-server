# Buildable Space Pipeline

`POST /buildable-space` is a synchronous flow that calculates:

1. the convex land remaining after server-owned per-edge setbacks; and
2. the best road-aligned usable rectangle on the configured local-Y search
   lattice.

It is independent from floor-plan generation, trials, SSE, candidate search,
solving, and scoring.

All dimensions are project units. The packaged configuration uses
`10 project units = 1 metre`. Areas are square project units.

## Accuracy contract

The usable rectangle is the deterministic optimum among candidates whose
lower and upper local-Y boundaries lie on the configured search lattice. It is
not claimed to be the continuous mathematical maximum. Candidate boundaries
are conservatively snapped inward to whole project units and containment is
validated again before returning.

## Regulatory status

The packaged `mock_residential_v1` setbacks are migration seed values copied
from the removed implementation. They are not verified Sri Lankan legal
requirements and must not be presented as regulatory advice. A legal profile
requires additional request/reference inputs such as jurisdiction, zoning,
road width, building height, site frontage, and ventilation conditions.

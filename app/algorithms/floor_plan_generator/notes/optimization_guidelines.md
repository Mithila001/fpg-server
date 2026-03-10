# Floor Plan Generator Optimization Guidelines

The core principle: constraints reduce the search space; objectives expand it

Every hard constraint cuts off branches the solver would otherwise explore. Every objective adds a new dimension the solver must optimise along. So in general:

* **more hard constraints → faster solving**
* **more/heavier objectives → slower solving**


## Constraint quality matters more than quantity

Not all constraints are equal. Ranked from most to least powerful:

1. **Global constraints** (e.g. `AddNoOverlap2D`, `AddAllDifferent`): highly efficient propagators.
2. **Equality / tight bounds** (`model.Add(x == y)`, tighter `NewIntVar` ranges): immediate deep propagation.
3. **Inequality** (`model.Add(x_end <= w_int)`): good propagation, but less tight.
4. **Reified / conditional** (`model.Add(…).OnlyEnforceIf(b)`): introduces boolean branching; useful but has overhead.
5. **Objective only** (`model.Minimize(cost)`): no propagation benefit; purely for solution quality.

Tighter variable domains are the single best thing you can do -- e.g., clamp room.max_w to
min(room.max_w, floor_width) to eliminate large portions of the search space.


## Hints: powerful but only when accurate

* A **good hint** (satisfying hard constraints) gives the solver a valid starting
  solution immediately. The search begins from there instead of from scratch.
* A **bad hint** (violates constraints) is ignored with no cost or benefit.
* Hints don’t improve propagation; they only speed up finding the first feasible
  solution in an optimisation run.

Hints work well combined with a time limit: you provide a decent starting point
and tell the solver to stop after, say, 0.5 s. You’ll usually get a near‑optimal
result without the full proof.


## Practical priority order for layout generation

1. Tighten variable domains.
2. Add strong global constraints (NoOverlap2D already present).
3. Add connectivity hard constraints (every room must touch at least one neighbour).
4. Set a time limit:
   ```python
   solver.parameters.max_time_in_seconds = 1.0
   ```
5. Add hints from previous solutions.
6. Add the `Minimize` objective.

With steps 1–5 done, the objective in step 6 starts from a much smaller search
space and an existing feasible solution, giving good quality quickly.


## What to avoid

* Many weak reified constraints with no propagation backbone; they add branching
  overhead without reducing the space.
* An objective without a time limit; the solver will search indefinitely to prove
  optimality.
* Loose variable bounds combined with a heavy objective.

---

This guideline should help you balance constraints, objectives, hints, and time
limits to keep the solver efficient without compromising result quality.
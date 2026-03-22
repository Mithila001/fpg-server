## ✅ Project walk-through: floor_plan_generator

The core module is generator.py, and it uses Google OR-Tools CP-SAT as the active solver.

---

## 🔧 Main purpose
- Generate a floor plan layout as a constraint optimization problem.
- Converts high-level `FpgRequirements` (rooms, sizes, coverage, etc.) into an OR-Tools model.
- Solves and emits room coordinates/dimensions.

---

## 🧱 Core features in this algorithm

1. `FloorPlanGenerator.__init__`:
   - Normalizes requirements via `rules.normalize_requirements`.
   - Sets floor dimensions/coverage.
   - Builds `Room` objects from input.
   - Adds mandatory system rooms:
     - `Living Room`
     - `Hallway`
   - Avoids duplicate types if user already defined them.

2. `generate()`:
   - Creates integer CP variables per room: x, y, width, height, x_end, y_end.
   - Adds constraints:
     - `add_basic_constraints` (non-overlap, in-bounds, min/max dims)
     - `adjacency_constraints` (relations from DB + mandatory/typed adjacency)
     - `add_minimum_area_coverage` (achieve min usable area)
     - `add_room_size_hierarchy` (size-related hard rule)
     - `add_hallway_constraints` (hallway-specific shape/use semantics)
   - Adds soft objective:
     - Center proximity (`add_center_proximity_objective`)
     - Living-room-touch penalty `_LIVING_MISS_PENALTY`
     - Hallway usage penalty `_HALLWAY_USAGE_PENALTY`
   - Solver parameters:
     - max 1 second
     - random seed and randomize search
   - Return `True` if solution is feasible/optimal.

3. `get_solution()`:
   - Pulls coordinates from solved variables.
   - Returns list of room dicts with layout positions and area.

---

## 🧩 Supporting components in this folder

- `rules.py`:
  - requirement normalizer and validation helper.
- `constraints/` submodules:
  - `basic_constraints` (room bounds, non-overlap)
  - `adjacency_constraints` (touching, allowed neighbors)
  - `floor_area_coverage`
  - `room_size_hierarchy_constraints`
  - `compact_layout` (center clustering objective)
  - `hallway_constraints` (hallway-specific requirements)
- `solver_models/room` data model.
- `types/room` request schema types.

---

## 🛠️ Active “OR-Tool” use

- Full solver stack:
  - `from ortools.sat.python import cp_model`
  - `cp_model.CpModel()`
  - `cp_model.CpSolver()`
  - `NewBoolVar`, objective minimization, `Solve()`
  - `cp_model.LinearExpr.Sum(...)`, penalties soft vs hard

So the main active tool is OR-Tools CP-SAT with constraints + custom objective.

---

## 🗺️ Quick flow summary 

1. API uploads `FpgRequirements`.
2. generator normalizes + builds rooms + mandatory rooms.
3. Make solver model with constraints + objectives.
4. Solve quickly (1s ceiling).
5. Extract and return room coordinates.

---

## Summery

- This is a constraint-based floor planner using OR-Tools.
- It enforces hard room rules and soft quality goals.
- Begins from room templates + DB adjacency constraints.
- Includes mandatory Living + Hallway behavior in solver.
- Output is a list of positioned rooms.

---


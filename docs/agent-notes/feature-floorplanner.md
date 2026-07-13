# Agent Notes: Feature - Floor Planner Core

## 1. Core class: `FpgrCore` in `app/algorithms/fpg_rooms/fpgr_core.py`
- Accepts `FpgRequirements` (rooms, config, relation_constraints).
- Normalizes requirements and applies hallway preparation via utility functions.
- Reads hard/soft constraint flags from config constants (`app/core/fpg_rooms/config_fpg.py`).
- Maintains internal state:
  - `self.rooms`: list of `Room` objects including generated `livingRoom` + hallways.
  - `self.model`: OR-Tools CP-SAT model.
  - `self.solver`: CP-SAT solver.
  - constraint toggles and envelope metadata.

## 2. Solve pipeline in `FpgrCore.solve()`
Steps:
1. room variable creation with `Room.create_variables()`.
2. optional `print_dev_log()` debug output.
3. hard constraints added conditionally:
   - `add_basic_constraints`
   - `add_hallway_constraints` (if hallway_count > 0)
   - `add_room_shared_wall_constraints`
   - adjacency, minimum area coverage, room size hierarchy, living room location, envelope/staircase constraints.
4. seed layout soft hints: `apply_seed_layout_hints_with_wiggle`.
5. build objective from soft constraints (center proximity, bathroom location, dead space, facade alignment/depth, shared wall refine).
6. set solver parameters (`max_time`, randomized search) and call `Solve()`.
7. status mapping (`OPTIMAL`, `FEASIBLE`).

## 3. Solution extraction: `FpgrCore.get_solution()`
- Asserts all position/size variables exist.
- Returns each room as dict:
  - `name`, `type`, `x`, `y`, `w`, `h`, `x_end`, `y_end`, `area`.

## 4. Constraints implementation files
- `app/algorithms/fpg_rooms/constraints/hard/`:
  - `basic_constraints`, `hallway_constraints`, `room_adjacency_hard`, `room_shared_wall_constraints`, `room_size_hierarchy_constraints`, `envelope_staircase`, `minimum_area_coverage`, `room_location_hard`.
- `app/algorithms/fpg_rooms/constraints/soft/`:
  - `bathroom_location_preference`, `compact_layout`, `layout_dead_space_penalty`, `recessed_facade_penalty`, `room_shared_wall_soft_refine`, `seed_facade_alignment_penalty`, `seed_facade_depth_penalty`, `seed_layout_hints`, `soft_room_adjacency`.

## 5. Pipeline integration points
- `FloorPlanGenerator` in `app/algorithms/fpg_rooms/__init__.py` likely wraps `FpgrCore` with stage orchestration.
- `app/services/algorithm_manager.py` and `algorithm_manager_v2.py` call the generator, then post-process:
  - `run_quick_post_process` -> compute wall geometries, connectivity.
  - `score_layout` and optional `run_refine_profile_1` in v2.
  - `generate_openings` and `run_final_post_process` for final output.

## 6. Notes for evaluation
- `should_bypass` logic in services indicates dev mode with mock JSON by default; `True` in prod may need toggling.
- `unit converter` ties API surface to internal solver units.
- `Optuna` and `refine` passes augment solver but complicate debugging; core generation is in `FpgrCore`.

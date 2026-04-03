# Agent Notes: Deep evaluation of `app/algorithms/fpg_rooms`

Summary: this document tracks core FPG module behavior, generated and refined solver flow, supporting submodules, and QA checklist.

## 1. Module overview
`app/algorithms/fpg_rooms` provides the main Floor Plan Generation (FPG) solver stack, including:
- `fpgr_core.py`: CP-SAT model assembly, constraint handling, objective function, and `solve()` lifecycle.
- `fpgr_p_generate.py`: generation profile (profile 1) that calls `FpgrCore` with basic soft options.
  - `FloorPlanGenerator.generate()` uses:
    - `seed_layout=None`, `wiggle_room=0`, `include_constraint_b_soft=False`, `debug_log=True`.
- `fpgr_p_refine_1.py`: refinement profile (profile 2) that re-runs `FpgrCore` seeded with stage-1 layout and includes additional soft heuristics.
  - `run_refine_profile_1()` behavior:
    - returns SKIPPED if no initial layout.
    - seed=initial layout with wiggle (default 10).
    - include A/B/C/D soft constraints and shared-wall soft.
    - if solve fails, returns `solved=False` with original rooms (fallback). 
  - two-pass refinement behavior via `run_refine_profile_1` in `algorithm_manager_v2`.
- `generator.py`: compatibility wrapper for public API `FloorPlanGenerator`.
- `solver_models/room.py`: per-room CP-SAT variable wrapper (`x, y, w, h, area, x_end, y_end, x_interval, y_interval`).
- `rules.py`: default normalization (min/max fallback from config constants).
- `types/room.py`: `RoomData`, `ConfigData`, `FpgRequirements` definition and config defaults mapping.
- `types/room_relations_constraints.py`: relation constraint Pydantic model (`RoomRelationsConstraint`).
- `utils/`:
  - generator helpers (hallway/living room injection), seed layout formatter, and requirement preparation.
- `fpg_optuna`: Optuna parameter search, `mutate_requirements`, prechecks, and `run_optuna_optimization` runner.
- `fpg_post_process`: quick + final wall union, compact+walls output, normalizing room/openings payloads.
- `fpg_score`: hard binary checks + range scoring for coverage/rectangularity/empty-space and gated final score.
- `constraints/hard` + `constraints/soft`: reusable modular hard and soft constraint builders (A/B/C/D/partial logic).

## 2. Data and config flow
1. API service collects user/DB inputs via `RoomSetupTemplate` and constraints.
2. `RoomData` objects are built and normalized (`rules.normalize_requirements`).
3. `FpgRequirements` is constructed, including `ConfigData` with constant defaults from `app/core/fpg_rooms/config_fpg.py`.
4. `FloorPlanGenerator` (via `fpgr_p_generate`) instantiates `FpgrCore` and runs solver.
5. Post-processing and openings functions convert solver room boxes into walls/openings payload.
6. Scoring can be applied to check geometry, coverage, overlap, and envelope.

## 3. `FpgrCore` constraint pipeline
### Construction
- Normalizes requirements and hallway setup via `generate_hallway_rooms` and `generate_living_room`.
- Applies defaults from config toggles: hard constraints and soft penalties can be toggled.
- Adds system rooms (living room/hallways) if missing.

### `solve()` order
1. create room CP variables (`room.create_variables`).
2. optional debug log.
3. Hard constraints (applied if configured true):
   - `add_basic_constraints`: non-overlap, within floor bounds, min/max dimensions.
   - `add_hallway_constraints`: ensures hallway design rules.
   - `add_room_shared_wall_constraints`: shared-wall adjacency rules.
   - `apply_hard_room_adjacency_constraints`: hard adjacency/hard OR/hard AND semantics.
   - `add_minimum_area_coverage`: coverage ratio constraint.
   - `add_room_size_hierarchy`: hierarchical min/max by type relative to living area.
   - `add_living_room_bottom_most_constraint`: living room position rule.
   - `add_envelope_staircase_constraints`: envelope guidance around external perimeters.
4. Seed constraints and soft hints - `apply_seed_layout_hints_with_wiggle`.
5. Soft objective terms (if enabled and relevant):
   - compact center proximity
   - bathroom location preference
   - dead space penalty (A)
   - seed facade depth/alignment (B/C/D)
   - soft shared wall refine
6. Minimize sum of objective terms with CP-SAT `Minimize(...)`.
7. Solver settings: random seed, randomized search, max time constant.
8. Solve and status detection.

## 4. `FpgCore` output
- `get_solution()` iterates rooms and returns a list of dicts with x,y,w,h,x_end,y_end,area.
- Asserts an all-required CP variable exists.

## 5. Refinement flow (`fpgr_p_refine_1`) and soft mode
- Uses first-run plan as seed input and re-runs with constraints A/B/C/D and shared-wall soft.
- If refinement fails, returns stage-1 layout unchanged.
- Helps tighten decorative rules while preserving feasibility.

## 6. Scoring and validation
- `fpg_score/scorer.py` layered scoring:
  - hard gating: geometry, overlap, adjacency, envelope.
  - geometric gate (air gaps, pockets): accept with suboptimal 1.0 score.
  - coverage/rectangularity/empty_space weighted final score.
- `fpg_score` includes invariants and thorough checks, while final payload may still be `status=SUCCESS` after soft violations.

## 7. Constraint implementation pattern
- Each constraint module func receives shared CP model and rooms; returns vars as needed.
- Hard constraints raise no exceptions but write constraints into model.
- Soft constraints return linear penalty terms that are summed into objective.
- `apply_hard_room_adjacency_constraints` handles hard AND/OR by parsing `relation_constraints` into A/B/C groups.

## 8. Project-level service orchestration
- `app/services/algorithm_manager.py`: uses DB CRUD + mock JSON fallback and runs pipeline with optuna or single-run.
- `app/services/algorithm_manager_v2.py`: strict API payload + pre_validation + optionally optuna refine.
- Both use `run_quick_post_process`, `generate_openings`, and `run_final_post_process` before returning API payload.

## 9. Observed design strengths
- clear hard/soft separation in constraint architecture
- reusability of modular constraint builders
- dynamic toggles from config for A/B/C modes
- staged pipeline for generate → refine → score → open

## 10. Potential risks / improvement spots
- `should_bypass=True` in prod-critical services can hide missing DB config.
- CP-SAT randomization may produce non-deterministic CI behavior; external seeding may help.
- `floor_plan_width`, `floor_plan_height` come from config defaults; must be validated upstream.
- Soft constraint terms combine with equal weight; more dynamic tuning or non-linear penalization may be needed.
- `normalize_requirements` does not validate min<=max semantics.

## 11. Latest review update
- confirmed fpg_rooms API is Task-centric with explicit pipeline states and well-documented soft/hard constraints.
- retested behavior path in mind: input template -> `build_requirements` -> `FpgrCore.solve` -> `post_process` + `generate_openings` -> API response.
- identified `FpgCore` as stateful but restartable, making profile-based refinement safe for fallback.
- added note to maintain explicit boundary/hallway config at service-time for consistency with generated `RoomData` bounds.
- documented that `fpg_post_process` can produce empty walls while still returning successful status; consumers should verify genre.

## 12. Remaining work
- Document `fpgr_p_generate.py` => exact `FpgrCore.solve` flags and profile A/B/C/D+shared-wall behavior.
- Document `fpgr_p_refine_1.py` => fallback style on failure and successive application of soft constraints.
- Expand constraints coverage for files in `constraints/hard` and `constraints/soft` with their numeric thresholds.
- Add detail on `fpg_post_process/processors` (`build_compact_data`, `run_wall_union`) and output shape transformations.
- Add detail on `fpg_score/binary_scoring` method-level hard violation triggers and scoring gating.
- Add `fpg_opening` contract and `algorithm_manager` cook flow for mock/DB routes.
- Add strong unit test mapping for existing tests and gaps (optuna bounds, refine fallback, scoring/hard-gate).
- Add known issue markers:
  - `normalize_requirements` min/max validation missing.
  - config override path for solver/toggle flags should be explicit.
  - stochastic CP-SAT seeds risk CI nondeterminism, consider external seed injection.
- Add full project mapping checkpoint (include algorithms: fpg_opening, fpg_rooms, usable_land_space_finder, fp_boundary_finder and service/route layers).
## 13. Additional module mappings
- `app/algorithms/fpg_opening`:
  - `OpeningGenerator` standalone API: takes room rectangles, finds livingRoom exterior sides, then CP-SAT solve for main door (priority cost), internal doors (candidate graph), and windows.
  - `generate_openings()` wrapper returns status/message/openings/warnings; no forced invalidation when only warnings.
  - Uses `or-tools` local solves with 1-second max and single worker.
- `app/algorithms/usable_land_space_finder`:
  - `find_usable_land_space()` shrinks convex polygon by directional/road offsets.
  - Requires 4+ boundary points and TA road-connected segment; validates convexity and positive remaining area.
  - Output: `shrunkSegmentsCoordinates`, metadata categories/offsets.
- `app/algorithms/fp_boundary_finder`:
  - `FPBoundaryFinder.fp_boundary_finder()` finds best axis-aligned rectangle (parallel/perp to TA edge) in polygon.
  - Pipeline: translate/reorder polygon, rotate to axis, sweep y, compute best rectangle in both orientations, inverse rotate/translate.
  - Resolution ***y_resolution*** controls precision/performance.

- `app/routes` + `app/services` layer mapping completed in algorithm_manager_v2 notes already; needs path to route endpoints for final integration check.

## 14. Next QA tasks
- Write unit tests for `FpgrCore.solve` flag combinations (hard/soft A/B/C/D/shared-wall), and ensure `seed_layout` + `wiggle_room` behavior is exercised.
- Add tests for `run_refine_profile_1` fallback path: unsolved -> drop back to initial layout.
- Add tests for `OpeningGenerator` categories: mainDoor, internalDoor, window candidate generation and failure warnings.
- Add tests for `find_usable_land_space` convexity and invalid shrink exceptions.
- Add tests for `FPBoundaryFinder` parallel/perpendicular comparing area and polygon orientation correctness.
- Add pipeline integration test for `algorithm_manager_v2.run_fpg_pipeline_api` in expected and invalid routes.

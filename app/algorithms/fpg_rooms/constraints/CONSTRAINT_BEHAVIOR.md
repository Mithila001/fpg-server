# AI Agent Note
If any constraint logic, parameters, toggles, or side effects change, update this file immediately.
If you find new behavior during debugging, add that finding under the relevant constraint section.

Status notes below are based on current wiring in fpgr_core plus current default toggles in config_fpg.

# Basic Geometry Constraints (basic_constraints.py)
- Type: Hard
- Currently Used: Yes (enabled by default)

## Description
Enforces global non-overlap across all rooms using AddNoOverlap2D.
Also binds derived coordinates (x_end, y_end) and applies aspect ratio bounds per room.
Hallways are excluded from aspect ratio checks.

## Parameters
model
rooms
MAX_ASPECT_RATIO_HEIGHT, MAX_ASPECT_RATIO_WIDTH
ROOM_TYPE_ASPECT_RATIO override map (garage, veranda)

## Constraint Impact
Creates the base geometric feasibility layer for the entire solve.
If this fails, no layout can be produced regardless of other rules.
Strongly restricts room shapes and blocks room overlap at all times.
Improves search quality by eliminating many invalid placements early.

# Hallway Constraints (hallway_constraints.py)
- Type: Hard
- Currently Used: Conditional Yes (runs when hallway_count > 0 and toggle is on)

## Description
For hallway rooms, enforces orientation logic (fixed narrow side, minimum long side).
Requires hallway contact with livingRoom and at least one non-living room.
Also enforces minimum number of fully shared hallway walls.

## Parameters
model
rooms
HALLWAY_WIDTH, HALLWAY_MIN_LENGTH, HALLWAY_REQUIRED_SHARED_WALLS

## Constraint Impact
Forces circulation corridors to be connected and realistic.
Can significantly tighten feasibility when hallway count is high.
Helps prevent isolated room clusters and unusable hallway placement.
Adds many touch and overlap literals, increasing model complexity.

# Room Shared Wall Constraints (room_shared_wall_constraints.py)
- Type: Hard
- Currently Used: Yes (enabled by default)

## Description
Applies per-room-type rules for minimum and maximum fully shared sides.
Measures overlap coverage on each side, then validates selected shared walls.
Supports wiggle percentage to relax required shared coverage length.

## Parameters
model
rooms
ROOM_SHARED_WALL_RULES (min_walls, max_walls, wiggle_pct per room type)

## Constraint Impact
Encodes enclosure and privacy behavior by room type.
Can remove layouts with too many exposed walls for key room types.
Adds dense pairwise side-overlap structure between rooms.
Strongly influences adjacency topology, not just position.

# Hard Room Adjacency Constraints (room_adjacency_hard.py)
- Type: Hard
- Currently Used: Conditional Yes (toggle on; effect depends on hard relation data)

## Description
Implements hard_and and hard_or adjacency requirements from relation constraints.
Uses side-touch booleans and minimum overlap to validate valid room contact.
Creates candidate adjacency switches and forces required OR groups.

## Parameters
model
rooms_list
hard_and_relations, hard_or_relations
DEFAULT_ADJACENCY_MIN_OVERLAP or provided min_overlap

## Constraint Impact
Directly controls mandatory functional relationships between room types.
Can make model infeasible if relation graph is too strict or contradictory.
Shapes final plan connectivity more than shape aesthetics.
Adds many conditional literals and OR constraints to the model.

# Minimum Area Coverage (floor_area_coverage.py)
- Type: Hard
- Currently Used: Yes (enabled by default)

## Description
Enforces lower bound on total room area relative to floor area.
Computes floor_width x floor_height and applies min_coverage threshold.
Requires sum(room.area) >= minimum required area.

## Parameters
model
rooms
floor_width, floor_height
min_coverage (default MIN_COVERAGE)

## Constraint Impact
Prevents sparse layouts with excessive unused floor area.
Couples all room area decisions into a single global bound.
Can conflict with strict size/location constraints in tight envelopes.
Improves overall utilization consistency across generated plans.

# Room Size Hierarchy (room_size_hierarchy_constraints.py)
- Type: Hard
- Currently Used: Yes (enabled by default)

## Description
Constrains target room areas as percentage bands of livingRoom area.
The livingRoom reference is now transported through normalized requirements and
no longer comes from hardcoded generator fallback constants.
For each configured room type, area must stay between min and max percent.
Skips gracefully if livingRoom is missing.

## Parameters
model
rooms
ROOM_SIZE_HIERARCHY mapping

## Constraint Impact
Locks relative room scaling around livingRoom as reference anchor.
Can prevent disproportionate room sizing even when geometry allows it.
Introduces cross-room area coupling across different room types.
Makes layouts more semantically balanced.

# Anchor Room Location Constraint (room_location_hard.py)
- Type: Hard
- Currently Used: Yes (enabled by default)

## Description
Enforces front anchor ordering via center-y comparison sum(y + y_end).
Uses veranda as anchor if present, otherwise livingRoom as fallback anchor.
All other rooms must be deeper than the selected anchor room.

## Parameters
model
rooms
(implicit veranda/livingRoom detection from room types)

## Constraint Impact
Controls macro depth ordering of the plan from front to back.
Stabilizes frontage semantics when veranda exists.
Reduces placement symmetry and random orientation drift.
Can limit alternatives in compact sites with many front-required rooms.

# Veranda Placement Constraints (hard_veranda_placement.py)
- Type: Hard
- Currently Used: Yes (enabled by default)

## Description
Pins veranda to front boundary at y = 0.
Creates verandaOutdoorSpace auxiliary room and forces one-side attachment.
Prevents verandaOutdoorSpace overlap with real rooms and enforces horizontal expansion side.

## Parameters
model
rooms
VERANDA_OUTDOOR_SPACE_MIN_W, MIN_H, MAX_W, MAX_H

## Constraint Impact
Adds extra solver room objects that affect geometry and scoring output.
Strongly governs frontage composition and outdoor interface behavior.
Can reduce feasibility if frontage is crowded by other hard rules.
Introduces non-overlap pressure with generated auxiliary geometry.

# Garage Placement Constraints (hard_garage_placement.py)
- Type: Hard
- Currently Used: Yes (enabled by default)

## Description
Enforces garage side anchoring with XOR on left or right boundary proximity.
Requires access path by either direct front placement or verandaOutdoorSpace front overlap.
Uses threshold-based side anchoring and full front-segment containment checks.

## Parameters
model
rooms
floor_width, floor_height
GARAGE_SIDE_ANCHOR_THRESHOLD

## Constraint Impact
Controls vehicular usability and legal-like frontage accessibility behavior.
Creates strong coupling between garage and outdoor frontage geometry.
Can become infeasible if garage, veranda, and envelope constraints conflict.
Greatly reduces garage placement ambiguity.

# Open Area Placement (Legacy, open_area_placement.py)
- Type: Hard
- Currently Used: No (legacy module, fully commented out, not wired in solver)

## Description
This file contains an older combined veranda and garage frontage constraint design.
Current source is commented out and has no executable constraint code.
Active logic has been split into hard_veranda_placement.py and hard_garage_placement.py.

## Parameters
Legacy target parameters were model and rooms.
It also internally derived land_width and land_height.
No active runtime parameters today because function is not executed.

## Constraint Impact
No current solver impact because this module is inactive.
Main value is historical reference for earlier combined frontage behavior.
Keeping it visible helps avoid duplicate reimplementation by agents.
Safe to ignore for live feasibility debugging unless revived.

# Envelope Staircase Constraints (envelope_staircase.py)
- Type: Hard
- Currently Used: Conditional Yes (toggle on and envelope_enabled True)

## Description
Builds outer envelope bounds from eligible rooms.
For exterior-facing room sides, enforces positive setback gap in [min_gap, max_gap].
Side application and exclusions are configurable by room type and side set.

## Parameters
model
rooms
floor_width, floor_height
min_gap, max_gap
exclude_types
apply_sides
ENVELOPE_* defaults

## Constraint Impact
Forces stepped perimeter behavior instead of flush outer walls.
Significantly shapes building massing and facade articulation.
Can heavily shrink feasible region when many rooms are exterior-exposed.
Adds complex blocker/exterior boolean logic per room pair.

# Seed Layout Hints With Wiggle (seed_layout_hints.py)
- Type: Soft (hinting + optional bounded guidance)
- Currently Used: Conditional Yes (toggle on and seed_layout provided)

## Description
Applies AddHint values for x, y, w, h from seed layout by room name.
If wiggle_room > 0, also bounds variable ranges around seed values.
Skips rooms not found in seed context.

## Parameters
model
rooms
seed_layout
floor_plan_width, floor_plan_height
wiggle_room

## Constraint Impact
Biases solver toward known-good layouts and speeds convergence in many cases.
With wiggle bounds, it can become quasi-hard guidance and narrow exploration.
Improves determinism when iterative refinement is desired.
No direct objective term, but strongly affects search trajectory.

# Soft Room Adjacency Preference (soft_room_adjacency.py)
- Type: Soft
- Currently Used: Partially (called when toggle is on; preference vars are not currently added to objective)

## Description
Creates adjacency preference boolean vars for soft relation pairs.
Reuses conditional touch logic with minimum overlap rules.
Returns preference vars to be consumed by objective construction.

## Parameters
model
rooms_list
soft_relations
DEFAULT_ADJACENCY_MIN_OVERLAP or provided min_overlap

## Constraint Impact
Encodes adjacency desirability without forcing strict feasibility.
At present, returned vars are not consumed in the objective, so impact is near-zero.
Low risk of infeasibility compared to hard adjacency mode.
To activate meaningful influence, these vars must be scored or constrained upstream.

# Compact Layout Center Proximity (compact_layout.py)
- Type: Soft
- Currently Used: Yes (enabled by default)

## Description
Adds objective cost for horizontal distance from floor center.
Also adds room.y term, biasing toward smaller y values (front side).
Returns sum of per-room compactness costs.

## Parameters
model
rooms
floor_width, floor_height

## Constraint Impact
Encourages tighter, centered clustering with front-leaning preference.
Can compete with back-depth or facade-based penalties.
Influences final objective strongly in under-constrained scenarios.
Does not create infeasibility, only ranking pressure.

# Bathroom Location Preference (bathroom_location_preference.py)
- Type: Soft
- Currently Used: Yes (enabled by default)

## Description
Penalizes bathrooms with low center-y by using max_center_y2 - (y + y_end).
Higher bathroom y-position lowers penalty under current coordinate orientation.
Weight is configurable and clamped to minimum 1.

## Parameters
model
rooms
floor_height
bathroom_weight (default BATHROOM_LOCATION_WEIGHT)

## Constraint Impact
Drives bathrooms away from front edge and toward deeper zones.
Usually improves privacy-oriented layout behavior.
May conflict with tight adjacency or seed constraints in small plans.
Pure objective term, so it reshapes ranking not feasibility.

# Layout Dead Space Penalty (layout_dead_space_penalty.py)
- Type: Soft
- Currently Used: Yes (enabled by default)

## Description
Computes bounding box around all rooms and penalizes empty area inside it.
Dead space = bbox_area - sum(room areas).
Returns weighted dead space penalty term.

## Parameters
model
rooms
floor_plan_width, floor_plan_height
dead_space_weight

## Constraint Impact
Pushes plans toward compact occupancy with less internal void.
Can compete with facade articulation penalties that prefer setbacks.
Encourages efficient packing without making model infeasible.
Global term couples all room placements through a shared bbox.

# Seed Facade Depth Penalty (seed_facade_depth_penalty.py)
- Type: Soft
- Currently Used: Conditional Yes (toggle on and seed_layout provided)

## Description
Uses seed facade-facing sets and penalizes recess depth from seeded facade lines.
Adds side-specific recessed penalties plus capped excess-count penalties.
Aggregates all terms and multiplies by depth weight.

## Parameters
model
rooms
SeedLayoutContext
floor_plan_width, floor_plan_height
depth_weight

## Constraint Impact
Helps preserve seed facade prominence and frontage continuity.
Discourages excessive recessing of facade-facing rooms.
Can conflict with envelope and shared-wall requirements.
Important for keeping generated plans close to facade intent.

# Seed Facade Alignment Penalty (seed_facade_alignment_penalty.py)
- Type: Soft
- Currently Used: Conditional Yes (toggle on and seed_layout provided)

## Description
For seed-neighbor pairs within alignment threshold, penalizes edge misalignment.
Checks left/right/top/bottom alignments based on seed overlap patterns.
Returns weighted sum of absolute edge-difference variables.

## Parameters
model
rooms
SeedLayoutContext
floor_plan_width, floor_plan_height
align_weight, align_threshold

## Constraint Impact
Preserves facade rhythm and edge continuity from seed design intent.
Improves visual alignment quality across related rooms.
Can reduce flexibility when seed data has noisy alignments.
Objective-only influence, so tradeoffs remain solvable.

# Recessed Facade Penalty (recessed_facade_penalty.py)
- Type: Soft
- Currently Used: Conditional Yes (toggle on and seed_layout provided)

## Description
Detects rooms near each facade in seed and penalizes excessive inward depth.
Applies base and severe depth penalties using separate thresholds and weights.
Also penalizes misalignment among nearby facade-neighbor room pairs.

## Parameters
model
rooms
SeedLayoutContext
floor_plan_width, floor_plan_height
near_band, base_threshold, severe_threshold
base_weight, severe_weight, attach_weight, side_gap_threshold

## Constraint Impact
Strongly controls facade step quality and prevents deep undesirable recesses.
Can dominate optimization when severe/base weights are high.
Works as a nuanced facade-quality metric beyond simple depth limits.
May conflict with compactness if both are weighted aggressively.

# Room Shared Wall Refine Penalty (room_shared_wall_soft_refine.py)
- Type: Soft
- Currently Used: Yes (enabled by default)

## Description
Applies refinement shared-wall expectations as a penalty instead of hard rule.
Computes per-room shortfall against refine min_walls and penalizes shortfall.
Reuses hard shared-wall touch and overlap utilities for consistency.

## Parameters
model
rooms
refine_rules (default ROOM_SHARED_WALL_RULES_REFINE)
refine_weight (default SOFT_ROOM_SHARED_WALL_REFINE_WEIGHT)

## Constraint Impact
Improves wall-sharing quality during refinement without hard infeasibility.
Gives solver room to trade slight violations against larger global gains.
Keeps objective pressure aligned with hard shared-wall semantics.
Useful for second-pass polishing behavior.
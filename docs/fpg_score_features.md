# FPG Room Scoring Features (app/algorithms/fpg_rooms/fpg_score)

This note summarizes how floor-plan layouts are scored in `app/algorithms/fpg_rooms/fpg_score/scorer.py`.

## 1) Score pipeline overview

1. Normalize input room records (`_coerce_room_record`) -> x/y/x_end/y_end/w/h/area
2. Run hard validations (binary checks):
   - `validate_room_geometry`
   - `validate_no_overlap`
   - `validate_adjacency_relations`
   - `validate_envelope_staircase_bounds` (if enabled)
3. If any hard violation: total_score = 0, valid=False.
4. Compute geometric gate checks:
   - `score_empty_space` (air gap detection)
   - `detect_inward_pocket_violation`
   - pattern: contains interior void or pocket violation => final returns 1.0 overall (still valid True)
5. If geometric gate passes, compute soft metrics and weighted final score.

## 2) Hard (binary) components

### 2.1 room_geometry
- `validate_room_geometry(solution, floor_width, floor_height)`
- Checks:
  - no non-positive width/height.
  - coordinate consistency: `x_end == x + w`, `y_end == y + h`.
  - rooms inside floor bounds `[0,floor_width] x [0,floor_height]`.
- Returns list of violation strings.

### 2.2 no_overlap
- `validate_no_overlap(solution)`
- Checks every pair of rooms to ensure x and y overlap do not both have positive intersection (no positive area overlap).
- If any overlap exists, report room pair and overlap amounts.

### 2.3 adjacency
- `validate_adjacency_relations(solution, relation_constraints, min_overlap)`
- For each room type with adjacency rules, for each required related type:
  - find candidate rooms of that type (excluding itself)
  - require at least one candidate touches with min overlap using `touches_with_min_overlap`.
- Missing related type or no sufficient touch -> violation.
- `min_overlap` default from `SCORE_VALIDATION_MIN_OVERLAP` (config default 20).

### 2.4 envelope/staircase bounds
- `validate_envelope_staircase_bounds(solution, min_gap, max_gap, exclude_types, apply_sides)`
- For eligible rooms (exclude list), find outer boundaries per side and ensure exterior rooms on each active side have gap in `[min_gap, max_gap]`.
- If an envelope-side room has a gap >0 but outside range => violation.
- Controlled by config: `ENVELOPE_ENABLED`, `ENVELOPE_MIN_GAP`, `ENVELOPE_MAX_GAP`, `ENVELOPE_EXCLUDE_TYPES`, `ENVELOPE_APPLY_SIDES`.

## 3) Geometric gate metrics

### 3.1 empty_space
- `score_empty_space(solution, floor_width, floor_height, wall_union, tolerance)`
- Builds room union shape via shapely.
- Defines boundary from union exterior.
- `air_gaps = boundary_shape.difference(union_shape)` -> area of enclosed space inside hull but outside rooms.
- If `air_gap_area > tolerance`: score = 1.0 (bad), else 100.0 (good).
- Diagnostic fields:
  - has_air_gap (0/1), air_gap_area, boundary_area, union_area, floor_area, tolerance, geometry_valid.

### 3.2 inward_pocket
- `detect_inward_pocket_violation(rooms, max_inward_length, tolerance)`
- Uses convex hull and union difference to find pockets.
- Finds boundary segments inside pocket that are on plan boundary and not on hull.
- Marks segments that represent inward pocket depth.
- If any pocket segment longer than threshold `max_inward_length` => violation True.
- Diagnostic fields include pocket_count, max_inward_segment_length, violating_segments etc.

## 4) Soft range scores (0..100)

### 4.1 coverage
- `score_coverage(solution, floor_width, floor_height, min_coverage)`
- `floor_area = max(1, int(floor_w) * int(floor_h))`
- `used_area = sum(int(room['area']))`
- `coverage_ratio = used_area / floor_area`
- if `coverage_ratio >= min_coverage`: score = 100.
- else score = `100 * (coverage_ratio / min_coverage)` (linear penalty down to 0).
- Diagnostic outputs floor_area, used_area, coverage_ratio, min_coverage.

### 4.2 rectangularity
- `score_rectangularity(solution)`
- `bbox_area` computed from min x,y and max x_end,y_end of all rooms.
- `ratio = clamp(used_area / bbox_area, 0..1)`.
- score = ratio*100.
- Diagnostics `used_area`, `bbox_area`, `rectangularity_ratio`.

### 4.3 empty_space
- Already in gate step. component `empty_space` uses same 100/1 metric.

## 5) Final total score
- `total_score = coverage*weight_coverage + rectangularity*weight_rectangularity + empty_space*weight_empty_space`
- Weights from `requirements.config.score_weights` or defaults (`SCORE_WEIGHTS`):
  - coverage: 0.40
  - rectangularity: 0.35
  - empty_space: 0.25
- Hard failures immediately yield `total_score=0`.
- Geometric gate air-gap/pocket failure yields `total_score=1`, but still valid apparently.

## 6) Key takeaways
- Hard constraints are gatekeepers before scoring.
- `empty_space` is now an explicit geometric gate: enclosed air gaps produce hard violations (and total=0).
- `inward_pocket` is still treated as geometric gate-signaling; pocket excess yields valid True with total=1 path.
- Adjacency/envelope are hard constraints (violations force total 0).


# Optuna Scoring Evaluation and Recommendations

## Goal of this review

This document evaluates how suitable the current Optuna scoring system is for
search optimization, and proposes practical improvements that keep the system
simple and reliable.

Scope of review:

- Current score pipeline in `app/algorithms/fpg_optuna_score`.
- How well each score section supports Optuna's trial-to-trial learning.
- Recommendations focused on signal quality, stability, and speed.

## Current scoring architecture (quick summary)

Total graph-stage score is out of 90:

- Floor plan zones: 30
- Outer clearance: 20
- Room relations: 30
- Spatial coverage: 10

Solver invocation gate:

- `usable_layout = total_score >= TRIAL_GRAPH_SOLVER_GATE_THRESHOLD`

This is a two-stage design:

1. Optuna samples points and receives graph score.
2. Only gate-passing layouts trigger the expensive solver stage.

Overall this is a good architecture for performance and safety.

## Section-by-section suitability for Optuna

## 1) Floor Plan Zones

Behavior:

- Per-room pass/fail by rule against zone cell placement.
- Section score is proportional to count of passed rooms.

Benefits for Optuna:

- Cheap to compute and deterministic.
- Strong domain priors are encoded explicitly.

Risks for Optuna:

- Mostly stepwise/binary reward creates flat regions.
- Small coordinate changes near boundaries can cause abrupt score jumps.

Suitability verdict:

- Good for hard guidance.
- Moderate for gradient-like learning.

## 2) Outer Clearance

Behavior:

- Uses discrete checks (front/back side clearance boxes).
- Aggregates evaluated components and normalizes to section max.

Benefits for Optuna:

- Easy-to-understand semantics.
- Captures required breathing space constraints.

Risks for Optuna:

- Binary-heavy outcomes often produce sparse feedback.
- Fallback scoring (for example kitchen vs hallway back opening) can inject
	discontinuities.

Suitability verdict:

- Good for rule compliance.
- Weak-to-moderate for smooth optimization pressure.

## 3) Room Relations

Behavior:

- Builds a relation graph, computes shortest paths for relation queries.
- Adds turn penalties and hallway privacy sub-score.

Benefits for Optuna:

- Rich structural signal (better than pure hard constraints).
- Gives Optuna a meaningful objective on circulation and relationship quality.

Risks for Optuna:

- High variance due to graph topology changes from small coordinate movement.
- Multiple interaction terms (path cost + turns + hallway privacy) can make the
	search landscape noisy.

Suitability verdict:

- High value section, but noisy.
- Strong candidate for careful smoothing/calibration.

## 4) Spatial Coverage

Behavior:

- Weighted blend of nearest-neighbor uniformity and grid probe gap.

Benefits for Optuna:

- Continuous metrics provide smoother trial feedback.
- Encourages global spread and reduces voids.

Risks for Optuna:

- Lower weight (10) means this smoother signal can be drowned out by
	high-variance sections.

Suitability verdict:

- Very Optuna-friendly signal.
- Under-leveraged due to relative weight.

## Overall suitability assessment

Current system is beneficial and usable for Optuna because:

- It has clear decomposition into interpretable sections.
- It supports efficient two-stage execution (graph gate then solver).
- It exposes diagnostics that can be mined for tuning.

Main limitation:

- The objective landscape is still relatively discontinuous in several places,
	so TPE may need many trials to reliably discover robust high-quality regions.

## Priority recommendations

## P0 (high impact, low-medium effort): smooth binary-heavy terms

Replace strict pass/fail chunks with distance-based partial credit where safe.

Examples:

- Zone scoring: if a room is outside its preferred zone, give decay credit by
	distance to nearest valid zone boundary instead of hard zero.
- Clearance scoring: convert blocker checks into penalty by overlap depth or
	minimum blocker distance.

Why:

- Increases local learning signal for Optuna.
- Reduces abrupt cliffs between nearly identical layouts.

## P1 (high impact, medium effort): stage-aware weighting schedule

Use dynamic section emphasis by trial phase:

- Early trials: slightly higher spatial coverage and zone weight for broad
	exploration and basic feasibility.
- Later trials: increase room relations influence for refinement.

Why:

- Better exploration-exploitation balance.
- Can reduce time spent in low-feasibility pockets.

## P1 (high impact, low effort): gate margin, not just gate pass/fail

Keep solver gate, but expose and use "distance to gate" consistently in trial
metadata and dashboards.

Why:

- Easier diagnosis of whether the optimizer is plateauing just below threshold.
- Helps tune section weights without blind trial count increases.

## P2 (medium impact, low effort): reduce objective noise from diagnostics side effects

Keep scoring function pure from side effects during most trials.

- Consider disabling heavy debug plotting for the common path.
- Keep plotting only for top-N or milestone trials.

Why:

- Faster and more stable optimization throughput.
- Cleaner signal when profiling per-trial runtime.

## P2 (medium impact, medium effort): relation score calibration

Calibrate relation path normalization and turn penalties using real trial
distributions (percentiles), not only static constants.

Why:

- Prevents either over-penalizing or under-penalizing path complexity.
- Improves comparability across floor sizes and room mixes.

## Suggested experiment protocol

Run A/B trials with fixed seeds and identical trial budgets:

1. Baseline (current).
2. Baseline + smoothed zone/clearance.
3. (2) + stage-aware weights.

Track:

- Best score at trial counts {10, 25, 50, 100}.
- Gate pass ratio.
- Solver pass ratio.
- Median per-trial runtime.
- Stability across 3-5 repeated runs.

Choose changes that improve both score quality and convergence reliability,
not only peak score in one run.

## Final recommendation

Keep the current sectioned architecture and solver gate.

For Optuna effectiveness, prioritize smoothing discontinuous score components
first, then add staged weighting. This gives the largest gain in practical
convergence without over-engineering the system.

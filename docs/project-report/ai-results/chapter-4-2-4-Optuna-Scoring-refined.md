# Chapter 4.2.4: Stochastic Layout Scoring System

The scoring architecture serves as the principal intermediary between stochastic search and deterministic architectural synthesis. Its role is to transform a proposed arrangement of room hint coordinates into a single, interpretable objective value that reflects how suitable the candidate layout is for downstream refinement. In practical terms, the sampler does not search the full geometry of the floor plan directly; instead, it explores a reduced spatial hypothesis space formed by representative room locations. The scoring layer evaluates those locations and provides a graded response that directs the sampling algorithm toward promising regions of the search space while avoiding configurations that are structurally weak or difficult to reconcile later. In the present implementation, this optimization layer is executed with Optuna.

This design is especially important because the optimization process is not purely decorative. The resulting hints are intended to support a later deterministic solving stage, which means the score must favor arrangements that are both architecturally plausible and computationally tractable. A binary pass-or-fail signal would be too sparse for this purpose. By contrast, a continuous objective produces a denser learning signal and helps the sampler distinguish between layouts that are almost acceptable and layouts that are fundamentally misaligned with the intended spatial logic.

## Centralized Scoring Manager

The implementation is organized around a centralized scoring manager that coordinates multiple specialized evaluators. This orchestration layer receives the sampled room coordinates, converts them into a normalized internal representation, and then dispatches the resulting point set to the individual scoring components. Each component evaluates one conceptual dimension of layout quality, returns a section score, and provides diagnostic information that can be inspected independently.

The value of this structure is methodological as much as computational. It allows the objective function to remain modular, transparent, and extensible. New scoring ideas can be introduced as additional evaluators without disturbing the interpretation of the existing sections, provided that the new contribution can be normalized onto the same overall scale. In that sense, the manager functions as a stable framework for future criteria such as daylight preference, facade alignment, or specialized adjacency preferences. The architecture therefore supports controlled evolution rather than one-off tuning.

## Score Composition and Acceptance Gating

The global objective function is composed of four score sections whose maximum values sum to $90$:

$$
S_{total} = S_{zone} + S_{clearance} + S_{relation} + S_{coverage}
$$

with the current distribution defined as:

- zone placement: $30$
- outer clearance: $20$
- room relations: $30$
- spatial coverage: $10$

This allocation is significant because it shows that the objective is not divided into a broad heuristic portion and a separate solver-derived portion. Instead, all four sections contribute to the overall objective itself, while the downstream deterministic solver is treated as a later gate in the workflow. Layouts that reach the required threshold are considered suitable candidates for the second stage; layouts below that threshold are treated as insufficiently promising and are not promoted for expensive verification. The gating mechanism therefore functions as a computational filter, not as a fifth score component.

## Zoning Score

The zoning score directs the sampler toward semantically appropriate parts of the floor plate for each room category. Its purpose is not merely to place rooms inside the building envelope, but to encourage a spatial vocabulary in which the function of each room aligns with its likely architectural role. Public or transitional spaces are allowed different positional freedoms from private or service-oriented spaces, and the zoning evaluator encodes that difference in a compact, geometry-driven form.

The current implementation uses a three-by-three conceptual grid over the floor area. Continuous coordinates are interpreted through that grid so that the sampler is not forced into a rigid discrete search, yet the resulting placements can still be evaluated against domain-specific occupancy rules. The present zoning logic focuses on the following implemented room rules:

- veranda: preferred along the bottom row of the grid,
- garage: preferred in the bottom-left or bottom-right zones,
- kitchen: allowed throughout the grid except the central cell,
- hallway: preferred away from the bottom row,
- living room: allowed in the lower two rows,
- bathroom: allowed throughout the grid except the central cell.

This structure reflects a simple but effective architectural intuition. Front-facing or access-oriented spaces are encouraged toward more exposed regions, while circulation and service spaces receive more flexible placement. The evaluator does not aim to exhaustively model every possible architectural convention; rather, it captures a small set of high-value spatial priors that are sufficiently strong to steer the sampler without overconstraining it. As a result, zoning acts as a coarse semantic scaffold for the rest of the optimization process.

## Outer Clearance Score

The outer clearance score addresses the relationship between selected rooms and the boundary conditions of the floor plan. Its role is to ensure that rooms requiring exposure, access, or a deliberate edge relationship are not placed in positions that would isolate them from the exterior or compress them into inconvenient interior pockets. From a design perspective, this component protects the envelope logic of the plan; from an optimization perspective, it prevents the sampler from repeatedly exploring layouts that violate obvious frontage expectations.

The current clearance evaluation is intentionally asymmetric, because not every room type carries the same boundary requirement. The implemented rules are as follows:

- veranda is checked for unobstructed space on its front side,
- garage is checked for unobstructed space on its front side,
- the back-opening condition is evaluated for kitchens and hallways,
- when both kitchen and hallway candidates exist, the strongest available back-opening result is retained.

The underlying concept is straightforward: a virtual clearance region is projected from the room center toward a designated side, and the evaluator checks whether other room points occupy that zone. Each violating point reduces the section quality, which makes the reward structure more informative than a strict pass-fail condition. The design is especially useful for the sampler because it preserves partial credit. A nearly correct frontage arrangement is therefore distinguished from a completely blocked one, and the sampler receives a meaningful gradient instead of a flat rejection.

Equally important is the treatment of absent optional rooms. If no room of a relevant type exists in the sampled layout, that sub-evaluation is skipped rather than forcing a misleading penalty. This prevents the score from conflating missing architectural program with positional inadequacy and keeps the section focused on actual geometric behavior.

## Room Relation Score

The room relation score is the most structurally expressive part of the objective because it models the plan as a network of functional relationships rather than as a set of isolated points. The main question is not simply whether two rooms are near one another, but whether the arrangement supports plausible movement, adjacency, and privacy gradients across the plan. This makes the relation score particularly valuable for layouts that must balance public circulation with private retreat and service efficiency.

Conceptually, the evaluator constructs a weighted graph whose nodes correspond to room points and whose edges encode relation preferences. The graph is then used to estimate circulation cost across a set of targeted room pairs. The shortest weighted path is preferred, but not every short path is equally good: sharp directional changes introduce additional penalties, which encourages smoother circulation trajectories. In symbolic form, the path cost can be understood as a combination of geometric distance and turn irregularity:

$$
C(P) = \sum_{(i,j) \in P} d_{ij}(1 + w_{ij}) + \lambda T(P)
$$

where $d_{ij}$ is the distance between successive room points, $w_{ij}$ is the relation weight, and $T(P)$ represents angular discontinuity along the path. The exact numerical form is less important than the architectural interpretation: rooms that ought to interact directly should require less circulation effort, while awkward detours should be discouraged.

The currently implemented relation rules include the following pairings:

- kitchen and dining room,
- living room and kitchen,
- living room and veranda,
- living room and bedroom,
- bedroom and attached bathroom,
- bathroom and living room.

In addition, hallway behavior is treated as a broader connective mechanism. Hallways are allowed to interact with a range of public and private room categories, and the scorer tracks how they participate in circulation routes. This provides an additional privacy-oriented dimension, because a hallway that mediates too many inappropriate crossings can be interpreted as a weak internal separator. The result is a relation score that captures both proximity and circulation quality, rather than one or the other alone.

This section is especially important for the overall system because it approximates a form of path planning before the deterministic solver runs. It encourages the sampler to produce a relational skeleton that is already compatible with architectural flow, thereby reducing the burden placed on later refinement.

## Spatial Coverage Score

The spatial coverage score acts as a counterweight to clustering. Without an explicit distributional constraint, optimization routines often compress points toward the center or toward locally convenient regions, which can leave the floor plate underutilized and create large empty regions that are difficult for the later solving stage to resolve cleanly. The purpose of this component is therefore to promote broad, stable occupancy across the full area of the plan.

The current implementation uses two complementary ideas. The first is nearest-neighbor distance, which measures how evenly the room points are spaced relative to one another and to selected boundary anchors. The second is grid-based coverage, which samples the floor area with a regular probe grid and checks how far each probe lies from the nearest room point. Together, these measures evaluate both local uniformity and global void formation. The section score is then formed as a weighted combination:

$$
S_{coverage} = 0.4S_{NND} + 0.6S_{grid}
$$

The boundary anchors are conceptually important because they prevent the evaluator from interpreting center clustering as optimal simply because interior-to-interior distances look neat. By including fixed reference points near the envelope, the score becomes more sensitive to layouts that leave the perimeter unused. This helps the sampler discover distributions that are both orderly and spatially expansive.

The practical effect is a more balanced point cloud. Room hints become neither overpacked nor excessively dispersed, and the candidate layout gains enough spatial breadth to support downstream partitioning. In the context of floor planning, this is a desirable compromise: the points should be sufficiently separated to preserve legibility, but not so scattered that the plan loses cohesion.

## Summary and Architectural Significance

Taken together, the four scoring sections create a disciplined objective that blends semantic placement, boundary appropriateness, circulation logic, and spatial distribution into a single optimization target. The system is effective precisely because each section addresses a different failure mode. Zoning prevents categorical mismatch, outer clearance protects edge relationships, room relations encode internal coherence, and spatial coverage discourages pathological clustering. The aggregated result is a score that is not merely high or low, but interpretive: it tells the optimization process why a layout is promising or why it remains weak.

This modular structure also ensures that the objective can mature alongside the project. If future architectural priorities emerge, they can be introduced as new evaluators without invalidating the existing scoring philosophy. For the Optuna-based search process, this is especially advantageous because the sampler benefits from a stable reward landscape that still admits controlled refinement. In that sense, the scoring system is not only a measurement tool; it is an active instrument of architectural guidance.

## Reviewer Notes

- Corrected the score allocation to match the active implementation: $30/20/30/10$ rather than a $90/10$ split.
- Treated the deterministic solver as a downstream acceptance stage, not as a scored component of the Optuna objective.
- Replaced implementation-level references with conceptual language and aligned the narrative with the currently implemented zoning, clearance, relation, and spatial coverage rules.

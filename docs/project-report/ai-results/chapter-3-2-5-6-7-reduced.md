# Condensed Chapter 3.2.5 to 3.2.7 Draft

## Chapter 3.2.5 Constraint-Based Floor Plan Generation Framework

The floor plan generator is the computational core of the project. It translates architectural intent into a feasible arrangement of rectangular rooms under geometric, relational, and stylistic constraints. Because the problem is combinatorial, the system must satisfy strict admissibility conditions while still leaving room for varied layouts. A constraint-programming approach solved through a CP-SAT engine is well suited to this task, since the search must respect exact relational rules rather than optimize a single continuous objective. Rooms must avoid overlap, honor mandatory adjacency, preserve frontage logic, and remain flexible enough to support multiple valid compositions.
The coordinate system is equally important. The origin lies at the bottom-left of the floor plate, the horizontal axis runs left to right, and the vertical axis measures depth from the frontage inward. Under this convention, $y=0$ represents the front edge of the plan. Several rules depend on this directionality, including entrance depth, frontage preservation, and the placement of rooms close to the exterior boundary. The model therefore treats geometry as semantically oriented rather than symmetric.
The generation pipeline is organized into two profiles. The first profile produces a fresh feasible layout from a requirement set. The second accepts an existing layout and improves it through a bounded re-solve that preserves overall composition while adjusting local relationships. This staged structure prevents the solver from treating every pass as unrestricted redesign. The configuration layer acts as a selection matrix that activates or deactivates families of rules without changing the solver architecture.

### Computational Core and Solver Logic

The core engine builds the constraint model, declares decision variables for each room, injects the selected rules, and searches for a feasible or improved arrangement. Each room is represented as a rectangle with linked position, size, boundary, and area variables, so the plan is handled as a coupled system of integer decisions rather than free-form polygons. The objective is a weighted sum of the active soft penalties,

$$
\min \sum_{k=1}^{n} \lambda_k C_k,
$$

with each term contributing only when soft guidance is enabled. If no soft terms are active, the solver performs pure feasibility search.
Initialization begins by normalizing requirement data and preparing the room set, including automatically introduced anchor spaces such as the living area and circulation elements. This ensures the solver reasons over a complete spatial topology instead of only the user-specified program. The search is randomized within a bounded time budget so that multiple plausible layouts can be explored without allowing one trial to dominate runtime.

### Phase I: Feasibility-Driven Synthesis

The initialization profile establishes a valid structural baseline. Its emphasis is on hard feasibility, with only limited soft bias, so it can discover a first workable arrangement without becoming overconstrained. Point-based hints provide a tentative spatial tendency, but they remain guidance rather than commitments. This allows the solver to begin near a promising region of the solution space while still retaining freedom to adjust the layout when necessary.
The profile prioritizes non-overlap, room-shape limits, adjacency logic, and frontage semantics before any aesthetic refinement is considered. In practical terms, the first pass is concerned with whether the plan is admissible at all. That makes it the most conservative stage in the system and the one most responsible for producing a usable baseline.

### Phase II: Iterative Layout Refinement

The refinement profile assumes a layout already exists and seeks local improvement without destroying the global structure. Instead of unrestricted repositioning, the solver is given limited spatial wiggle around the prior solution. This produces outputs that remain recognizably related to the original composition while still allowing meaningful adjustment.
Refinement introduces a richer set of soft preferences. These encourage useful alignments, reduce wasted area, maintain facade clarity, and improve shared-wall quality. The same solver can therefore support iterative design development: each pass may polish the arrangement a little further, and several passes can be chained when gradual improvement is preferred over one large redesign.

### Constraint Formalization and Taxonomy

The constraint system translates architectural intent into an admissible spatial configuration. It is best understood as two tiers. Hard constraints establish the non-negotiable feasibility envelope, while soft constraints influence ranking among otherwise valid candidates. A violation of a hard constraint invalidates the plan; a violation of a soft constraint only reduces desirability.

#### Hard Constraints

Geometric feasibility ensures that rooms remain internally consistent, non-overlapping, and compatible with their declared dimensions. Aspect-ratio limits prevent rooms from becoming unrealistically thin or flattened, and differentiated tolerance for garages and verandas reflects the fact that some room types may legitimately be more elongated than standard interior spaces. This level is foundational because all higher-order reasoning depends on a reliable notion of extent.
Circulation and connectivity rules keep hallway-like spaces functional. A hallway must preserve a narrow dimension, retain a sufficiently long complementary dimension, and connect to the principal living area together with at least one other non-living room. Boundary sharing is also checked so that the circulation spine feels integrated rather than isolated.
Directional rules govern how the plan relates to the frontage and the exterior. The frontage side is treated as the front of the house, with deeper rooms positioned inward from it. When a veranda exists, it becomes the primary anchor; otherwise, the living area serves that role. Additional rules regulate veranda-to-outdoor alignment, garage placement near a lateral boundary with access from the front, controlled perimeter staggering, and a protected service-side setback for kitchen or circulation backs. Together, these constraints preserve a legible front-to-back hierarchy and a coherent exterior massing.
Functional adjacency rules define the house’s internal graph. Mandatory relationships require substantial shared boundary contact rather than accidental point touch, and alternative relations allow a compatible member of a room group to satisfy the requirement. This keeps the layout usable while preserving flexibility in exact placement.

#### Soft Constraints

Soft constraints shape preference rather than validity. Adjacency affinity rewards useful proximity without forcing a single configuration. Compactness keeps rooms near the central axis and moderates excessive lateral spread. Residual void minimization discourages inefficient empty space inside the enclosing boundary. Seed-conditioned guidance transfers prior positional knowledge into the search, while facade depth conservation and boundary alignment preservation keep useful edge relationships stable during refinement. Recess modulation and boundary-coupling reinforcement further improve facade rhythm and shared-wall quality without converting these ideas into rigid constraints.

### Summary

The generator is the most structurally demanding part of the system because it must reconcile geometry, function, and design intent within one optimization framework. Its strength lies in the interaction between feasibility constraints, staged refinement, and soft architectural preferences. The first profile establishes a valid spatial foundation, the second polishes that foundation with limited movement, and the overall constraint architecture keeps the result practical and expressive.

## Chapter 3.2.6 Post-Processing Refinement Stage

The post-processing stage sits between generation and scoring. Its purpose is to repair layouts that are feasible in principle but still contain local geometric defects such as fragmented circulation, misaligned boundaries, decimal drift, or weak frontage alignment. Rather than forcing the generator to resolve every detail upfront, the refinement layer applies limited corrections that preserve the plan’s spatial logic while improving usability and evaluation stability. It is best understood as conservative geometric repair rather than redesign.

### Extended Wall Refinement

Extended wall refinement allows selected room boundaries to grow when a small extrusion improves continuity or adjacency. The operation is bounded by room-type priority and configuration limits, so only a limited number of rooms, wall candidates, and extrusion distances are considered. This makes the process selective: it can enrich a room outline, but it cannot distort the whole plan.

### Hallway Union

Hallway union addresses fragmented circulation. When adjacent hallway segments share enough overlapping boundary, they are merged into a single circulation component. The result is clearer, more faithful to architectural convention, and less likely to be penalized by later scoring.

### Snap Floor Plan to Grid

Grid snapping regularizes coordinates by projecting them onto a fixed lattice. If $g$ is the grid spacing, then $x' = g \cdot \mathrm{round}(x/g)$ and $y' = g \cdot \mathrm{round}(y/g)$. This removes floating-point noise introduced by geometric operations and improves numerical stability without changing the plan in any meaningful architectural sense.

### Veranda Adjustment and Wall Union

Veranda adjustment checks whether the veranda and its outdoor transition space are actually adjacent before any correction is applied. When alignment exists, the veranda frontage can be shifted to match the width of the adjoining outdoor region, improving continuity and reducing awkward projections. If the relationship is absent, the system leaves the geometry unchanged.
Wall union then consolidates overlapping or duplicate boundary traces into one structural network. This prevents double counting, yields a clearer wall representation, and provides a stable base for opening placement and boundary validation.

### Overall Evaluation of the Refinement Pipeline

Taken together, the refinement pipeline balances flexibility with control. It repairs local defects, strengthens geometric coherence, and preserves the logic of the original generation stage. Its purpose is not to replace constraint-based synthesis, but to make its output more usable and more stable for scoring.

## Chapter 3.2.7 Floor Plan Score

The scoring stage is the final evaluation layer after post-processing. It decides whether a generated floor plan is structurally sound enough to proceed and assigns a score that reflects both hard geometric validity and a smaller functional review. The system is split into a critical domain and a basic functional domain. The critical section remains the gatekeeper: only plans that pass all required geometric checks can receive the supplementary functional score.
The central scoring orchestrator receives normalized rooms, boundary information, and requirement parameters. If normalization yields no viable rooms, or if the geometry is too irregular for evaluation, the process stops immediately. Otherwise, three critical checks are applied: adjacency, empty space, and inward pockets. Their results are normalized to a 25-point critical section using $S_{critical}=25\cdot p/n$, where $p$ is the number of passed checks and $n$ is the number executed. This keeps the evaluation transparent and evenly weighted.
Adjacency verifies that required room relationships are present and that contact is substantial enough to count as meaningful. Empty-space scoring detects internal voids by comparing the covered area of the rooms with the enclosing boundary, rejecting plans with gaps beyond tolerance. Inward-pocket scoring measures concavity in the outer boundary by comparing the room union with its convex hull and flags recesses that exceed a maximum permitted length.
If, and only if, the critical section is perfect, a basic functional score contributes the remaining 75 points. This stage reviews three high-level usability relations: the balance of the living area, the adequacy and consistency of bedroom spaces, and the relationship between the kitchen and dining area. The intent is to recognize stronger residential layouts without allowing functional preference to override structural validity.
Overall, the scoring system combines hard geometric validation with a modest functional supplement. It preserves reliability first and then rewards layouts that are both coherent and practically usable.

## Reviewer Notes

- Reduced all three chapters to tighter academic prose while preserving the core technical meaning.
- Removed extended elaboration and duplicate framing to better fit the requested word-count targets.
- Kept formulas and gate logic intact, but compressed descriptive passages where the underlying logic did not change.

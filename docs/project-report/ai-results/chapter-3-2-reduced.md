# Chapter 3.2.1 Client–Server Interaction and Communication Flow

The client organizes user input, coordinates asynchronous computation on the server, and converts returned planning data into a compact visual preview. Its role is intentionally light on computation and focuses instead on input preparation, job orchestration, progress mediation, and presentation.

The interaction begins with site definition. The user adjusts the polygon and scale locally until the plot matches real dimensions, then specifies road access and requests buildable-space evaluation under setback and spatial rules. This task runs as an asynchronous server job: the client submits the geometry, receives a job identifier, and monitors progress through streamed events and status polling. The combined approach preserves responsiveness while keeping the user informed during initialization, layout synthesis, refinement, scoring, and completion.

After successful evaluation, the client receives a usable area that bounds later floor planning. It then supports room configuration by allowing required program elements and floor dimensions within the derived limits. A lightweight client-side check provides immediate feasibility feedback and reduces unnecessary submissions.

Floor-plan generation follows the same pattern. Requests include dimensional constraints, aspect preference, and a room template; the server returns a job token and performs optimization. The client continues to consume progress updates and can recover state after interruption by polling the job endpoint. A persistent browser identifier links requests to a session, and running jobs may be cancelled when design requirements change.

When generation completes, the server returns room polygons, partitions, labels, and openings. The client normalizes units and converts these outputs into drawing primitives for rendering. By separating interaction, computation, and presentation, the system remains responsive, traceable, and easy to revise.

# Chapter 3.2.2 Build Requirement

The build requirement stage is the pre-processing layer of the floor plan generation pipeline. It does not produce geometry directly; instead, it converts a loosely specified request into a validated, solver-ready requirement package. By normalizing room definitions, floor dimensions, and relational constraints before generation begins, the stage reduces infeasible trials and keeps the design brief internally consistent.

At a high level, the stage validates the room template, retrieves constraint knowledge stored on the server, and adjusts the request so that all values are compatible with generation. The result is a consolidated requirements object used in optimization, scoring, and post-processing.

#### Validation

Validation first checks whether the template contains the mandatory room categories required for meaningful generation. Typical examples include a sleeping room, kitchen, bathroom, and veranda or another access-related space. These categories provide the minimum semantic structure needed for adjacency, circulation, and boundary relationships. Without them, the constraint system lacks sufficient information to build a viable household composition.

This step also prevents the solver from operating on incomplete templates. Because the optimization stage is constraint-driven, missing structural elements can create infeasible relationships later in the pipeline. Validation therefore protects both logical consistency and computational efficiency.

#### Dimension Calculation and Aspect Ratio

A second function of the stage is to estimate a suitable floor envelope from the room composition. This is important because the search space grows rapidly with available area. If the boundary is too large, the solver must explore many more placements, which reduces efficiency and weakens solution quality. To limit this effect, the system reduces the effective floor space according to the minimum spatial requirements implied by the room set.

Let the minimum width and height of room $i$ be $w_i^{\min}$ and $h_i^{\min}$, with corresponding maximum values $w_i^{\max}$ and $h_i^{\max}$. A conservative lower bound on the area required by the template is

$$
A_{\min} = \sum_{i=1}^{n} w_i^{\min} h_i^{\min} + A_{\text{buffer}}.
$$

Likewise, an upper bound is

$$
A_{\max} = \sum_{i=1}^{n} w_i^{\max} h_i^{\max} + A_{\text{buffer}}.
$$

The buffer term allows for circulation loss, alignment overhead, and auxiliary spacing.

The aspect ratio is handled through a feasibility test against the buildable envelope. If the requested ratio is

$$
r = \frac{H}{W},
$$

then the system seeks a rectangle that respects both the ratio and the available limits. Given maximum width $W_{\max}$ and maximum height $H_{\max}$, the feasible width must satisfy

$$
W \le W_{\max}, \qquad W \le \frac{H_{\max}}{r}, \qquad W \le \sqrt{\frac{A_{\max}}{r}}.
$$

The selected width is therefore

$$
W^* = \min\left(W_{\max},\, \frac{H_{\max}}{r},\, \sqrt{\frac{A_{\max}}{r}}\right),
$$

and the corresponding height is $H^* = rW^*$. If the resulting rectangle still fails to meet the minimum required area, the request is rejected as geometrically incompatible.

#### Load Server Constraints

Once the request is geometrically valid, the system loads server-side constraints for each room type. Room-size constraints define admissible width, height, and area ranges under a given size label, while relation constraints describe how one room should interact with others through mandatory or preferential enforcement levels. These constraints form part of the solver’s objective and feasibility structure.

#### Majority Size Selection and Prune Relations

The stage also normalizes room size labels. If several labels appear in a template, the most frequent one is promoted as the dominant category and applied to the remaining rooms except where a special case is preserved. This reduces heterogeneity and stabilizes the constraint set.

Relation constraints are then pruned so that only relationships relevant to the active template remain. This prevents the solver from enforcing rules involving absent room types and keeps the knowledge base aligned with the current request.

#### Assemble Final Package

After validation, geometric adjustment, constraint loading, size normalization, and relation pruning, the stage assembles the final requirements package. It contains the normalized room list, validated configuration values, and filtered relation constraints. This package becomes the canonical input for later phases of the floor plan pipeline.

Overall, the build requirement stage transforms an informal design brief into structured optimization input and ensures that the solver operates within a meaningful and feasible search domain.

# Chapter 3.2.3 From Geometric Synthesis to Hint-Based Exploration

The first optimization stage in the floor plan generation pipeline produces spatial hints rather than final room geometry. Its purpose is to search for favorable candidate locations that a constraint-based solver can later interpret as soft guidance. The optimization engine therefore acts as a probabilistic search mechanism over a reduced layout space, where each trial proposes a possible configuration of point-based hints inside the floor boundary.

This design responds to a practical constraint. Direct optimization of full room dimensions required substantial time per trial because each attempt combined generation, post-processing, and scoring in a costly cycle. The revised strategy shifts the target toward hint discovery, which lowers the cost of each trial and allows a much larger number of candidates to be explored within the same runtime budget.

The workflow is best understood as a two-level search. At the first level, the sampler proposes coordinates for the relevant spatial entities. These coordinates are not fixed placements; they indicate preferred regions from which the downstream solver may infer room arrangement. At the second level, the solver checks whether the hinted configuration can be realized under the geometric and relational constraints of the project. This separation makes the process more efficient because the expensive solving step is reserved for candidates that already show structural promise.

#### Search Space Parametrization and Discretization

The search space uses reduced resolution rather than continuous sampling. If the floor extent is denoted by $W$ and $H$, and the grid spacing by $\Delta$, candidate positions are restricted to values of the form $x = x_0 + k\Delta$ and $y = y_0 + m\Delta$, where $k$ and $m$ are integers. This discretization lowers the number of admissible states, keeps sampled hints separated by a practical distance, and aligns the sampler with the granularity expected by the solver.

The sampling parameters are therefore best understood as spatial bounds, grid resolution, and hint radius. Together, they shape the search landscape so that the optimization engine focuses on broad structural relations rather than excessive geometric precision.

Each trial returns a continuous evaluation of the sampled hint arrangement. This score measures how well the proposed hint map supports a plausible layout and allows the sampler to distinguish between weak, moderate, and strong candidates over successive trials.

#### Evaluation Workflow and Procedural Refinement

When a trial exceeds the solver gate, the sampled hints are passed into the solver as soft guidance. If the solver constructs a valid floor plan, the result is combined with the earlier sampling score. If the solver fails, the trial still contributes through the sampling score, preserving information from partial failure.

The sampler is used in a focused manner. Its role is not to model every architectural rule, but to learn from previous candidate quality and bias later trials toward more useful point patterns. The coarse lattice also regularizes the process by preventing redundant trials that differ only by negligible offsets. Each trial therefore proceeds as: propose a coordinate set, evaluate it against structural heuristics, and, if promising, pass the corresponding hints to the solver for exact realization.

Persistent storage is disabled by default, which matches the exploratory character of the optimization stage. The design emphasizes the interplay between coarse spatial sampling, gate-based solver invocation, and score-driven refinement.

#### Summary

In summary, the optimization stage bridges abstract spatial exploration and exact constraint-based generation. By transforming full geometry synthesis into hint discovery, the system gains a larger trial budget, a more informative learning signal, and a better match between exploratory search and solver execution. The low-resolution search space, continuous scoring, and selective solver invocation together produce floor plan candidates that are computationally tractable and structurally meaningful.

# Chapter 3.2.4: Stochastic Layout Scoring System

The scoring architecture is the interface between stochastic search and deterministic architectural synthesis. It converts a proposed arrangement of room-hint coordinates into a single objective value that indicates how suitable the candidate layout is for later refinement. Rather than searching the full floor-plan geometry directly, the sampler explores a reduced hypothesis space of representative room locations. The scoring layer evaluates these locations and guides the search toward promising regions while avoiding structurally weak or difficult layouts. In the current implementation, this optimization layer is executed with Optuna.

This approach is necessary because the optimization stage is not decorative. The generated hints must support a later deterministic solving stage, so the score must favor layouts that are both architecturally plausible and computationally tractable. A binary pass-or-fail signal would be too sparse. A continuous objective provides a denser learning signal and helps the sampler distinguish between layouts that are nearly acceptable and those that are fundamentally misaligned.

## Centralized Scoring Manager

The implementation is organized around a centralized scoring manager that coordinates multiple specialized evaluators. It receives sampled room coordinates, converts them into a normalized internal representation, and dispatches the resulting point set to individual scoring components. Each component evaluates one dimension of layout quality, returns a section score, and provides diagnostic information for inspection.

This structure keeps the objective modular, transparent, and extensible. New scoring ideas can be added as additional evaluators without disturbing the interpretation of existing sections, provided they are normalized to the same scale. The manager therefore supports controlled evolution rather than one-off tuning.

## Score Composition and Acceptance Gating

The global objective consists of four score sections whose maximum values sum to $90$:

$$
S_{total} = S_{zone} + S_{clearance} + S_{relation} + S_{coverage}
$$

with the current distribution defined as:

- zone placement: $30$
- outer clearance: $20$
- room relations: $30$
- spatial coverage: $10$

All four sections contribute to the overall score, while the deterministic solver acts as a later gate. Layouts that meet the required threshold are promoted to the second stage; layouts below it are treated as insufficiently promising. The gate therefore functions as a computational filter, not as a fifth score component.

## Zoning Score

The zoning score directs the sampler toward semantically appropriate parts of the floor plate for each room category. Its purpose is not only to place rooms inside the envelope, but to encourage a spatial vocabulary in which function aligns with architectural role. Public or transitional spaces are given different positional freedoms from private or service-oriented spaces, and the zoning evaluator encodes that difference in a compact, geometry-driven form.

The current implementation uses a three-by-three conceptual grid over the floor area. Continuous coordinates are interpreted through that grid so the sampler is not forced into rigid discrete search, yet placements can still be evaluated against domain-specific occupancy rules. The implemented room rules are: veranda in the bottom row, garage in the bottom-left or bottom-right zones, kitchen anywhere except the center, hallway away from the bottom row, living room in the lower two rows, and bathroom anywhere except the center.

This reflects a simple architectural intuition: front-facing or access-oriented spaces are encouraged toward more exposed regions, while circulation and service spaces receive more flexible placement. Zoning therefore acts as a coarse semantic scaffold for the rest of the optimization process.

## Outer Clearance Score

The outer clearance score addresses the relationship between selected rooms and the floor-plan boundary. It ensures that rooms requiring exposure, access, or a deliberate edge relationship are not placed where they would be isolated from the exterior or compressed into interior pockets. From a design perspective, this protects envelope logic; from an optimization perspective, it prevents repeated exploration of layouts that violate obvious frontage expectations.

The current evaluation is intentionally asymmetric: veranda and garage are checked for unobstructed space on their front side, while kitchen and hallway are evaluated through a back-opening condition. When both kitchen and hallway candidates exist, the strongest available back-opening result is retained.

A virtual clearance region is projected from the room center toward a designated side, and the evaluator checks whether other room points occupy that zone. Each violating point reduces the section quality, which makes the reward structure more informative than strict pass-fail logic. If no room of a relevant type exists, that sub-evaluation is skipped rather than forcing a misleading penalty.

## Room Relation Score

The room relation score is the most structurally expressive part of the objective because it models the plan as a network of functional relationships rather than isolated points. The main question is not only whether rooms are near one another, but whether the arrangement supports movement, adjacency, and privacy gradients across the plan.

The evaluator constructs a weighted graph whose nodes correspond to room points and whose edges encode relation preferences. The graph estimates circulation cost across targeted room pairs. The shortest weighted path is preferred, but sharp directional changes add penalties, encouraging smoother circulation trajectories:

$$
C(P) = \sum_{(i,j) \in P} d_{ij}(1 + w_{ij}) + \lambda T(P)
$$

where $d_{ij}$ is the distance between successive room points, $w_{ij}$ is the relation weight, and $T(P)$ represents angular discontinuity along the path.

The currently implemented pairings include kitchen and dining room, living room and kitchen, living room and veranda, living room and bedroom, bedroom and attached bathroom, and bathroom and living room. Hallways are treated as broader connective mechanisms and are allowed to interact with a range of public and private room categories.

## Spatial Coverage Score

The spatial coverage score counters clustering. Without distributional constraints, optimization routines often compress points toward the center or locally convenient regions, leaving large empty areas that are difficult for later solving to resolve cleanly. This component promotes broad, stable occupancy across the full plan.

The current implementation combines nearest-neighbor distance and grid-based coverage. Nearest-neighbor distance measures how evenly room points are spaced relative to one another and to selected boundary anchors. Grid-based coverage samples the floor area with a regular probe grid and checks how far each probe lies from the nearest room point. Together, they evaluate local uniformity and global void formation. The section score is:

$$
S_{coverage} = 0.4S_{NND} + 0.6S_{grid}
$$

Boundary anchors prevent the evaluator from treating center clustering as optimal simply because interior-to-interior distances appear neat. This makes the score more sensitive to unused perimeter space and helps the sampler discover distributions that are orderly and spatially expansive.

## Summary and Architectural Significance

Together, the four sections create a disciplined objective that blends semantic placement, boundary appropriateness, circulation logic, and spatial distribution into a single optimization target. Each section addresses a different failure mode: zoning prevents categorical mismatch, outer clearance protects edge relationships, room relations encode internal coherence, and spatial coverage discourages pathological clustering. The result is an objective that is interpretable rather than merely high or low.

This modular structure also allows the objective to evolve with the project. If new architectural priorities emerge, they can be added as new evaluators without invalidating the existing scoring philosophy. For the Optuna-based search process, this is advantageous because the sampler benefits from a stable reward landscape that still admits controlled refinement.

## Reviewer Notes

- Reduced each section to a tighter academic register while preserving the original technical meaning.
- Consolidated repeated explanations and removed nonessential elaboration to meet the requested word-count targets.
- Kept formulas and scoring structure intact, but simplified phrasing where the meaning remained unchanged.

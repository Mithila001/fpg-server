# Chapter 3: Methodology

## 3.1 Overview

This chapter describes the methodological design of the floor plan generator system. The system integrates four principal subsystems: land usability analysis, requirement construction, guided sampling, and final plan refinement. Together these subsystems translate client requirements and site constraints into an actionable architectural layout.

The methodology is structured around a layered pipeline:

- identification of usable build area from raw boundary data,
- construction of normalized generation requirements from database-sourced templates and constraints,
- dimensional validation and search-space reduction to produce a feasible optimization domain,
- Optuna-driven sampling of room hint coordinates,
- constraint-solver floor plan generation with hard and soft constraints,
- post-processing to repair topology defects,
- final scoring and delivery of validated results.

The overall process can be viewed as a data-driven cascade: each stage filters and conditions the input before passing it to the next stage, which improves robustness and reduces wasted computation. The system explicitly decouples geometric feasibility from architectural quality, ensuring that only candidate layouts with both structural validity and spatial coherence are returned to the client.

This workflow balances the combinatorial nature of layout generation with the need to avoid large infeasible search spaces. It uses statistical sampling to recommend promising layouts, then applies exact constraint solving and post-hoc repair to obtain buildable floor plans.

## 3.2 Buildable Land Space Finder

The first stage addresses the physical land context. The system receives polygonal site boundaries and an access line, then computes the maximum usable interior footprint. The access line represents the road or terrain connection and is used to orient the solution.

The land-space algorithm uses a geometric classification process. Boundary segments are classified into categories such as front-facing, rear-facing, and side-facing based on their orientation relative to the access line. This classification influences how the usable area is shrunk and where the final rectangle can be placed.

The land analysis pipeline performs the following steps:

1. boundary extraction and validation,
2. convexity enforcement for usable interior geometry,
3. iterative offsetting of the boundary inward,
4. segmentation classification by direction,
5. search for the largest axis-aligned rectangle that lies entirely within the shrunken polygon.

The usable land space is represented as a polygon with a reduced buffer from the original boundary. The buffer is computed from the classified segments, so the system preserves suitable setback distances along the front, sides, and rear. The goal is to produce a buildable rectangle that satisfies the site-specific edge constraints while maximizing area.

The rectangle search is a specialized geometric optimization: from a set of candidate interior points, the algorithm tests feasible axis-aligned rectangles and returns the largest one. This rectangle becomes the effective floor plan boundary for the remainder of the pipeline.

By converting irregular site geometry to a simplified internal rectangle, the generator avoids the overhead of solving floor plans in complex nonrectangular domains. The land finder therefore acts as a preprocessing filter that preserves feasibility while providing a realistic origin for floor layout generation.

Mathematically, the buildable land stage can be conceptualized as follows. Given an original polygon $P$ and a set of segment offsets $d_i$, the usable polygon $P^{*}$ is defined by the Minkowski contraction:

\[
P^{\*} = P \ominus B,
\]

where $B$ is a buffer set built from the directional offsets. The rectangle search then seeks an axis-aligned rectangle $R$ such that $R \subseteq P^{*}$ and the area $A(R)$ is maximized. This reduces the problem from arbitrary polygon packing to a constrained rectangle selection problem.

## 3.3 Algorithm Manager for Floor Plan Generation

The central subsystem is the algorithm manager. It orchestrates the full floor plan generation flow from client input to solver execution. Its responsibilities include requirement construction, validation, configuration, and pipeline control.

### 3.3.1 Build Requirement Workflow

The generation process begins with a requirement builder. It transforms raw input parameters from the client into a normalized requirement object.

Client inputs typically include:

- target floor width and height,
- desired aspect ratio,
- a room setup template describing required room types,
- optional hints about preferred room placement.

The requirement builder merges this input with persisted metadata from the database. Metadata sources include dimension constraints, room relations, and template definitions.

The workflow has these phases:

- data retrieval,
- constraint normalization,
- mandatory room validation,
- dimension sanitization,
- configuration assembly.

At the end of this phase, the system holds a single requirement object that captures the entire problem instance.

### 3.3.2 Database Data Retrieval

The system retrieves three types of database data:

- size constraints for rooms,
- room relation constraints,
- layout templates.

Size constraints encode minimum and maximum widths, heights, and area ranges. They are essential to ensure that the solver generates rooms of realistic proportions.

Room relation constraints encode adjacency and connectivity expectations. These relations are not simple label assignments; they capture the desired spatial graph of the plan. For instance, certain rooms may be preferred to be adjacent, while others should avoid direct adjacency.

The layout template provides the concrete set of room identifiers and types. The template may specify combinations such as bedrooms, bathrooms, kitchen, living room, dining room, garage, and veranda spaces.

By isolating database access from the solver logic, the manager makes the generation process repeatable and easier to debug.

### 3.3.3 Data Preprocessing

Preprocessing is a crucial step that converts database rows and raw input into solver-ready structures.

The following operations are performed:

- numeric coercion of widths, heights, and areas,
- expansion of null or missing template values into fallback defaults,
- translation of relational constraints into pairwise spatial influence weights,
- computation of room area minima and maxima,
- assembly of initial hint coordinate sets.

This stage is also responsible for constructing the initial point-hint map. Optuna operates on points rather than full room polygons, so the builder extracts the information needed to seed the sampler.

### 3.3.4 Data Validation and Cleanup

Validation removes invalid requests early. The system performs both syntactic and semantic checks.

Syntactic validation confirms that the payload contains the required fields and that numeric values are within expected types. Semantic validation checks that:

- required room types are present in the template,
- room dimension ranges are coherent,
- the aggregated minimum area does not exceed the maximum available floor area.

The cleanup process removes or transforms invalid fields. For example, null maximum dimensions may be replaced by a safe default, and string-encoded numbers are converted to numeric form.

### 3.3.5 Crafting Configurations

The requirement object is augmented with a configuration profile. This profile includes:

- validated floor boundary dimensions,
- an effective search grid scale for optimization,
- scoring thresholds,
- trial count and solver-control parameters.

The configuration encapsulates both the physical problem and the solver’s operational parameters. It enables the same requirements to be used consistently across the Optuna sampler, the solver, and the scoring modules.

### 3.3.6 Floor Dimensions and Search Space Reduction

A core aim is to avoid an excessively large search space. The system computes feasible floor bounds that are smaller than the raw maximum dimensions when possible.

The calculation begins with the total minimum room area:

\[
A*{min} = \sum*{i=1}^{n} a\_{i}^{\text{min}},
\]

where $a_{i}^{\text{min}}$ is the minimum area for room $i$.

The maximum allowed floor area is:

\[
A*{max} = W*{max} H\_{max}.
\]

If $A_{min} > A_{max}$, the problem is rejected as infeasible. Otherwise, the generator derives a minimum feasible width and height pair $(W_{min}, H_{min})$ subject to aspect ratio bounds:

\[
\alpha*{min} \leq \frac{W}{H} \leq \alpha*{max}.
\]

A simple feasible pair is obtained by solving:

\[
W*{min} H*{min} = A\_{min}
\]

with the aspect ratio constraint. The system chooses values that minimize the search domain while respecting the ratio bounds.

This reduction is important because Optuna’s performance is highly sensitive to the volume of the continuous search space. By limiting the domain to an area that is close to the minimum required, the method ensures the sampler focuses on plausible layouts.

### 3.3.7 Floor Bound Validation

Floor bound validation functions as a feasibility gate. It verifies that the provided and derived dimensions form a valid envelope. This includes checking:

- the client-specified width and height are positive and within practical limits,
- the computed minimum width and height are feasible given the aggregated room demands,
- the final envelope honors the configurable aspect ratio range.

If the validation fails, the system returns a clear, deterministic error rather than attempting optimization. This avoids wasted trials and ensures clients receive immediate feedback when their specification is impossible.

## 3.4 Optuna-Based Floor Plan Generation Floor

The central layout generation stage uses a two-stage process: Optuna sampling of room hint coordinates, followed by solver-based plan generation from those hints.

### 3.4.1 Optuna Sampling

The first stage uses Optuna to explore the room-hint search space. The system treats each trial as a proposal of point coordinates for each room.

The sampled parameters are primarily the $(x, y)$ coordinates for each room’s hint. These points are sampled uniformly within the validated floor boundary. The search is discretized by a configured grid scale so that each coordinate lies on a coarse lattice.

The reason for this is twofold:

- it reduces the effective number of possible positions,
- it aligns the sampling resolution with the solver’s internal grid.

The parameterization is intentionally simple. The sampler does not attempt to place full room geometry or enforce all adjacency constraints directly. Instead, it generates a skeleton of spatial preferences that the subsequent solver uses as a starting point.

Optuna is used because it offers adaptive search for high-dimensional continuous spaces. It can exploit promising regions through successive trials while maintaining exploration. The library’s built-in handling of trial history, objective propagation, and pruning makes it well suited to this kind of heuristic search.

### 3.4.2 Optuna Scoring System

The objective function is critical. It evaluates each trial and returns a scalar score that measures the layout skeleton’s quality. The score is composed of multiple sections, each representing a different aspect of architectural quality.

The sections are:

- zone placement scoring,
- outer clearance scoring,
- room relation scoring,
- spatial coverage scoring.

The final Optuna score is intentionally constructed so that approximately 90% of it measures layout quality and 10% measures feasibility potential. This gives the sampler a strong preference for well-formed candidate hints while still allowing feasibility to influence the outcome.

#### 3.4.2.1 Zone Placement Scoring

Zone scoring evaluates whether room hints are placed in regions of the floor plan that are consistent with their functional role. Public rooms such as living rooms, dining rooms, and kitchens receive higher scores when they are closer to the front or center of the envelope. Private rooms such as bedrooms and bathrooms are scored based on their ability to form coherent quieter zones.

This is implemented via normalized coordinate functions. For each room point, the algorithm computes relative distances to the floor boundaries and ideal zone centers. The score contribution is a smooth function of these distances, such as a Gaussian or piecewise linear penalty.

The smoothness is important because it creates a continuous objective surface for Optuna to optimize. A candidate point near an ideal zone receives nearly full credit, while a point far away receives a continuous penalty rather than a binary rejection.

#### 3.4.2.2 Outer Clearance Scoring

Outer clearance scoring penalizes points that are too close to the floor boundary. The motive is to avoid rooms that would be squeezed against the exterior edge or that would create awkward interior circulation.

The score is based on distance to the envelope edges and can be computed as:

\[
S*{clearance}(p) = \sigma\left(\min*{e \in \text{edges}} d(p, e)\right),
\]

where $d(p, e)$ is the distance from point $p$ to edge $e$ and $\sigma$ is a monotonic smoothing function.

This reward encourages more balanced layouts and reduces the likelihood that the solver will later produce boundary-adjacent pocket spaces.

#### 3.4.2.3 Room Relation Scoring

Room relation scoring uses the adjacency graph from the database. For each pair of related rooms, the system scores the proposed hint coordinates according to their pairwise distance and relation type.

A simple utilitarian model is to assign a penalty for distance in the form:

\[
S\_{relation}(i, j) = \frac{1}{1 + \beta \cdot d(p_i, p_j)},
\]

where $d(p_i, p_j)$ is the Euclidean distance between room hints and $\beta$ is a scale parameter derived from the relation weight.

Crossing relations or contradictory pairings are also penalized. If the room graph suggests a particular circulation path, the scoring function checks whether the sampled points approximate that path.

This module is dynamic because the same scheme is applied to different templates and different relation densities. The system automatically adjusts the effective weight of each relation based on the number of relations and the room types involved.

#### 3.4.2.4 Spatial Coverage Scoring

Spatial coverage scoring measures how well the sampled points cover the floor area. It penalizes clumping and rewards distribution across the envelope.

The metric can be formalized as a coverage function over a grid or via pairwise separation distances. The objective is to avoid layouts where many rooms are placed in the same region, which would make the solver struggle to allocate area.

The combination of all scoring sections yields a performance signal that balances functional correctness, zone appropriateness, and feasibility.

### 3.4.3 The Role of Smooth Scoring

The system deliberately avoids binary valid/invalid scoring at the Optuna stage. Boolean scoring would create a discontinuous objective surface with large flat regions and sharp cliffs, making it difficult for the sampler to discover incremental improvements.

Instead, each scoring component returns a continuous score. This gives each trial an informative gradient: a layout can be partially good even if it is not fully feasible. That allows Optuna to climb toward better configurations gradually.

The smooth scoring philosophy is especially important in a high-dimensional layout problem because it mitigates the curse of dimensionality. Even poor candidates contribute information, which reduces the chance of wasted trials.

### 3.4.4 Floor Plan Generation Process

When Optuna discovers a high-scoring hint map, the system begins the floor plan generation phase. This phase attempts to convert the hint coordinates into a full rectilinear plan using a constraint solver.

The generation process is structured as follows:

1. seed the solver with the hint points,
2. run an initial generation under hard constraints,
3. if feasible, enter refinement with soft constraints,
4. if not feasible, optionally retry with the same hint map.

The hint map is treated as a set of preferred centers rather than fixed room placements. The solver uses them to orient room positions but still solves for exact widths, heights, and adjacency.

#### 3.4.4.1 Initial Generation with Hints

The initial generation phase uses the following hard constraints:

- minimum and maximum room dimensions,
- non-overlap between rooms,
- boundary containment within the floor envelope,
- mandatory adjacency and circulation relations,
- alignment constraints for rectilinearity.

This phase attempts to satisfy all of these constraints simultaneously. Because the solver is based on a satisfiability-modulo-theories style search, it can find an exact feasible placement if one exists.

The hints influence the solver by seeding the search with approximate target coordinates. This keeps the solution within the general region predicted by Optuna and reduces the effort needed to satisfy the constraints.

#### 3.4.4.2 Multiple Attempts for Same Hint Map

The methodology allows multiple solver invocations for a single hint map. This is because the solver’s internal search may be non-deterministic and because a slightly different exploration path may find a feasible layout where a previous path failed.

The system typically performs a small number of retries on the same map. This increases robustness without excessively increasing runtime.

#### 3.4.4.3 Hard Constraints and Adaptability

The hard constraints are expressed abstractly so that different room templates can be handled with the same mechanism. For example:

- the same containment constraint applies to any room type,
- the non-overlap constraint is pairwise and symmetric,
- adjacency requirements are encoded as relational pairs with weights.

This design means the floor plan generator can handle simple layouts and complex multi-room plans with equivalent logic. The constraint expressions can be evaluated for any combination of rooms, making the system template-agnostic.

### 3.4.5 Refinement Profile

When an initial feasible plan exists, the method proceeds to refinement. The plan is treated as a seed and adjusted to improve quality in small steps.

#### 3.4.5.1 Soft Constraints Used in Refinement

Refinement optimizes soft qualities such as:

- improved adjacency fidelity,
- better room shape aspect ratios,
- reduced unused interior buffer space,
- improved circulation flow.

These soft constraints are not required to be satisfied perfectly. They guide a local search that seeks a better plan without changing the topology of the feasible solution.

#### 3.4.5.2 Hard Constraints During Refinement

Hard constraints remain enforced during refinement. This ensures that every intermediate plan is still valid with respect to room dimensions, non-overlap, and boundary containment.

This dual enforcement allows the refiner to treat hard constraints as invariants while soft constraints are optimization objectives.

#### 3.4.5.3 Movement Restriction and Search Reduction

The refinement stage deliberately restricts the amount of change permitted in each iteration. This is done by limiting the permitted movement of room edges and the amount of size adjustment.

The rationale is that a feasible plan already has the correct global structure. Large changes could break that structure and force the solver to re-solve a much larger problem. By only allowing subtle adjustments, the search is effectively local and the runtime is reduced.

This local refinement can be viewed as a trust-region method in numerical optimization: the current plan defines a neighborhood, and only modifications within that neighborhood are evaluated. This makes the process efficient and stable.

### 3.4.6 Floor Plan Post Processing

Even after refinement, some floor plans still contain geometric imperfections. The post-processing stage addresses these residual issues.

#### 3.4.6.1 Motivation for Post Processing

The constraint solver ensures feasibility, but it does not always provide the most usable geometry. Common artefacts include internal air gaps, inward pockets, and nonoptimal wall alignments. These issues occur because the solver is optimizing a symbolic constraint system rather than the continuous geometry directly.

The post-processor is therefore a corrective layer. It inspects the realized room polygons and repairs topological defects that are not captured by the original solver constraints.

#### 3.4.6.2 Post Processing Features

The post-processing system is composed of several geometric repair mechanisms:

- hallway union and simplification to reduce redundant internal boundaries,
- wall extension to close narrow indents and regularize the perimeter,
- snapping to a grid to align vertices and improve rectilinearity,
- veranda and outdoor-space adjustment to maintain consistent exterior interfaces.

Each feature is applied conditionally based on the detected defects. For example, if narrow nonconvex pockets appear along the outer wall, wall extension can remove them. If internal corridors are overly fragmented, union operations can merge them into a coherent circulation path.

The process preserves the validity of the original plan while improving its usability. It is intentionally conservative: the post-processor does not rewrite the whole layout, but rather corrects local geometric anomalies.

### 3.4.7 Floor Plan Scoring

The final scoring step evaluates the generated plan at the most detailed level.

The scoring system is hierarchical and includes both hard verification and qualitative assessment.

#### 3.4.7.1 Hard Verification

The first scoring layer verifies that the plan is geometrically valid. It checks:

- that every room polygon is rectilinear,
- that there are no overlaps between rooms,
- that all rooms fit within the outer boundary,
- that prescribed adjacency relations still hold.

This layer serves as a final gate: any plan failing these checks is rejected.

#### 3.4.7.2 Qualitative Scoring

The second layer evaluates quality metrics. These include:

- room shape appropriateness (aspect ratio regularity),
- circulation quality,
- spatial distribution and coverage,
- adjacency coherence,
- compliance with target zoning patterns.

Each metric has a scoring function that returns a continuous value. The final score is an aggregate of these component scores.

Because the system uses continuous scoring, it can distinguish between different valid plans and prefer the better one. This is important when multiple feasible solutions exist for the same requirements.

#### 3.4.7.3 Scoring Rationale

The scoring logic is designed to reward architectural sensibility. For example, a plan that places the kitchen adjacent to the dining area and the living room near the front entrance scores higher than a plan where these relationships are inverted.

Similarly, plans with fewer internal air gaps and smoother room shapes receive higher scores. The objective is to prefer plans that would be practical to build and comfortable to inhabit.

## 3.5 Final Results to Client

The last stage packages the selected plan for delivery. The response contains:

- the finalized room polygons,
- the computed score and scoring breakdown,
- any metadata such as solver status and post-processing actions.

The system only returns plans that have passed the full pipeline. If no candidate passes, it returns a deterministic failure response with an explanation of the limiting factor.

This final delivery preserves transparency and reliability. The client receives a concrete floor plan plus evidence that the plan was validated through both optimization and refinement.

## 3.6 Workflow Summary

The methodology follows a staged pipeline designed for robustness and usability. It begins with physical site feasibility, proceeds through constraint-driven generation, and concludes with quality-focused repair and scoring.

The main methodological contributions are:

- a buildable-land preprocessor that converts site geometry into a usable rectangle,
- normalized requirement construction from database-driven room templates and relation constraints,
- search-space reduction through computed floor bounds,
- Optuna-guided sampling of room hint coordinates with smooth objective scoring,
- a two-phase floor plan generation process with hard constraint feasibility followed by soft constraint refinement,
- a post-processing repair layer for geometric defects,
- hierarchical scoring and deterministic result delivery.

This architecture is intended to produce floor plans that are both feasible and architecturally meaningful, while avoiding wasted computation on infeasible or low-quality layouts.

## 3.7 Evaluation and Practical Considerations

The methodology is designed with practical performance constraints in mind. The most expensive components are the Optuna sampling stage and the solver-based generation stage. To keep runtime acceptable, the system uses a limited number of trials and several levels of early rejection.

Key practical design choices include:

- early floor bound validation to reject infeasible configurations before optimization,
- grid-based sampling to reduce the continuous search space,
- repeated solver attempts only when the hint map is promising,
- local refinement with restricted movement rather than global reoptimization.

These measures make the system suitable for interactive and near-real-time scenarios, where clients expect responses within a few seconds to a few minutes.

### 3.7.1 Constraint Programming and Topology

The solver portion of the pipeline is built on a constraint programming paradigm. Constraint programming excels at satisfiability and structured feasibility, but it has limitations when it comes to continuous topology.

As a result, the solver can produce plans with valid discrete relations but with undesirable continuous geometry. For example, internal air gaps occur because the solver is not directly optimizing the union of room polygons; it only ensures pairwise non-overlap and boundary containment. Inward pockets appear because the solver satisfies local room placement constraints without penalizing nonconvex boundary shapes.

The post-processing stage is therefore essential. It applies topological repair to the discrete solver output and closes the gap between symbolic feasibility and continuous usability.

### 3.7.2 Use of Optuna as a Heuristic Layer

Optuna is used not as a final decision engine, but as a heuristic layer that recommends promising room seed positions. This is an important architectural choice.

The method leverages Optuna’s ability to search high-dimensional continuous spaces while avoiding the need to encode all layout constraints into the search itself. The solver still handles exact feasibility. This separation of concerns improves scalability: the heuristic layer guides the search, and the exact layer verifies and formalizes the result.

### 3.7.3 Future Extension Points

The methodology naturally supports future extensions. Potential improvements include:

- richer scoring modules for acoustic zoning, daylighting, or privacy,
- multiple land shapes beyond axis-aligned rectangles,
- integration of cost or construction metrics,
- adaptive trial budgets based on early success rates.

Each extension can be integrated into the existing pipeline without changing the underlying stage boundaries.

## 3.8 Conclusion

This chapter has described the methodology behind the floor plan generator. It emphasizes a structured pipeline that moves from physical site viability through normalized requirement construction into guided optimization, exact floor plan generation, refinement, repair, and scoring.

The system is designed to maximize both reliability and usability. By applying multiple filters and by separating heuristic guidance from exact solving, it produces floor plans that satisfy complex architectural requirements while maintaining performance.

The central system is the algorithm manager. It assembles the full floor plan generation pipeline from client inputs, persisted constraint data, and solver primitives.

### 3.3.1 Build Requirement Workflow

The generation process begins with a build requirement manager that constructs a normalized requirements object from the request payload. Client-provided values include floor width, floor height, aspect ratio, and a room template representing the desired layout type.

The manager retrieves database data such as room size constraints, room relation constraints, and room setup templates.

- size constraints define allowable widths, heights, areas, and aspect ratios for each room type,
- relation constraints encode spatial relationships between rooms (adjacency, connectivity, and relative orientation),
- setup templates specify the concrete room list and their intended roles.

This data is loaded from the server-side repository and then normalized into a unified requirement structure. During this stage, validation ensures mandatory room types are present, numeric values are sanitized, and invalid values are rejected immediately rather than silently defaulted.

### 3.3.2 Database Retrieval

Database retrieval is isolated from the generation logic. The manager bypasses optional caching for deterministic behavior and loads the following sets of metadata:

- mandatory room templates for the chosen layout,
- room dimension constraints for the template,
- graph-based room relations representing adjacency or flow.

These categories are combined and pruned. The resulting requirement set contains only the constraints that are relevant for the current layout, removing unused or conflicting rows. This pruning keeps the solver’s input compact and avoids unnecessary search complexity.

### 3.3.3 Data Preprocessing

Preprocessing transforms both static constraints and input dimensions into forms that downstream components can use directly.

Key preprocessing operations include:

- coercing numeric parameters into validated floats,
- extracting effective min/max width and height bounds for each room,
- computing per-room area constraints,
- assembling an adjacency-aware representation of room relationships.

This stage also builds initial hint positions when present: the optimizer can accept a sparse set of point hints for rooms, which are later used as soft seeding for the solver.

### 3.3.4 Validation and Cleanup

Validation operates at two levels: API-level and optimization-level.

The API-level validation checks the completeness and consistency of the incoming request. It verifies that essential room categories are included in the template and that the raw floor dimensions are within acceptable limits.

The optimization-level validation computes workable floor bounds using both the configured maximum dimensions and the aggregated minimum area demand derived from room constraints. It performs the following reasoning:

- compute the sum of minimum room areas,
- compare it against the maximum floor area implied by the client’s width and height,
- if the minimum demand exceeds the maximum area, flag the request as infeasible.

When the computed bounds are feasible, the system derives a minimal floor width and height that satisfy both area and aspect ratio constraints. This reduces the effective search space for the optimizer by avoiding unrealistically large or skewed floor dimensions.

### 3.3.5 Crafting Configurations

A configuration profile is constructed from the validated requirements. It contains:

- the floor boundary dimensions,
- the allowable aspect ratio range,
- per-room minimum and maximum dimensions,
- global solver settings such as grid scale and trial counts.

This configuration is passed to the optimization stage intact. It is the single source of truth for the floor plan generator and ensures that both the sampling stage and the solver interpret the same boundaries and constraints.

### 3.3.6 Floor Dimension Calculations and Search Space Reduction

One of the core contributions of this methodology is the attention to floor bounds.

Rather than allowing the optimizer to explore the full envelope of the provided width and height, the system calculates a feasible subspace by using the combined minimum room areas and the target aspect ratio range. The bounds calculation addresses several issues:

- it prevents excessively large search domains that slow down Optuna sampling,
- it avoids extreme aspect ratios that can lead to degenerate layouts,
- it ensures the solver only receives dimensions that are consistent with the actual room demands.

In practical terms, the algorithm computes:

- a required floor area equal to the aggregated minimum room areas,
- an additional area buffer to maintain shape flexibility,
- a minimum width and minimum height such that the area and aspect ratio constraints are satisfied.

When the request is accepted, the optimization domain is therefore a rectangular region that already encodes feasibility heuristics. This dramatically increases the probability that later stages can generate a valid floor plan.

### 3.3.7 Floor Bound Validation

Floor-bound validation is treated as a gatekeeper. It rejects configurations that would force the system into unsolvable regimes.

The validation relies on both the raw user-provided dimensions and the derived bounds from the room constraints. It enforces the idea that the floor plan must fit within both the maximum allowed envelope and the minimum required envelope. If either condition fails, the generation pipeline stops early.

This validation reduces wasted compute on high-level layout sampling when the input data itself is infeasible.

## 3.4 Optuna-Based Floor Plan Generation

The core layout generator is an Optuna-driven process. The system uses Optuna as a metaheuristic sampler for room hint coordinates, rather than as a full combinatorial solver. In this design, Optuna provides a candidate spatial skeleton, and a separate constraint solver turns that skeleton into an actual floor plan.

### 3.4.1 Why Optuna?

Optuna is chosen because it provides a robust framework for guided exploration across continuous and discrete domains. It supports:

- flexible parameter spaces,
- interpretable objective functions,
- trial-level scoring with pruning or scheduling,
- grid-aware sampling through custom step sizes.

The methodology favors Optuna because the room-hint coordinate space is high-dimensional and nonconvex. Traditional exhaustive search would be infeasible for a realistic number of rooms. Optuna’s sequential model-based optimization helps concentrate effort on promising regions while still maintaining diversity in the search.

The optimization is therefore not a direct solver for room placement; it is a recommendation engine for room hints.

### 3.4.2 Optuna Sampling

The Optuna sampling routine primarily samples spatial positions for each room hint. Each trial proposes a set of coordinates inside the validated floor boundary. These coordinates are interpreted as the approximate center of a room, or as the location where a room should be seeded.

The sampled parameters include:

- x and y coordinates for each room or room group,
- search bounds enforced by the floor envelope,
- optional discretization scale to reduce search granularity.

The method uses uniform sampling across the available space, constrained by a search grid. The grid scale is configured to align with the solver’s internal resolution, which helps the downstream solver accept hints without excessive quantization error.

Sampling is intentionally kept broad rather than overly room-specific. The goal is not to pre-place exact room geometry, but to generate a skeleton of preferred regions that the solver can then realize.

### 3.4.3 Optuna Scoring System

The scoring system is critical to the optimization loop. It converts a proposed hint layout into an objective value that guides Optuna toward desirable arrangements.

The system is modular and composed of several scoring contributions:

- floor plan zone scoring,
- outer clearance scoring,
- room relation scoring,
- spatial coverage scoring.

Each scoring module evaluates a different aspect of the candidate layout.

#### 3.4.3.1 Floor Plan Zone Scoring

Zone scoring measures whether sampled points are positioned in appropriate regions of the floor.

For example, public functions such as living rooms, kitchens, and dining rooms should be placed in zones with good access and openness. The algorithm computes normalized coordinates relative to the floor dimensions and rewards positions that align with typical zoning heuristics.

This module uses smooth penalty functions rather than binary accept/reject thresholds. Distance from ideal zone centers and boundary proximity are converted into continuous scores. This provides Optuna with a gradient-like objective surface rather than a sparse reward.

#### 3.4.3.2 Outer Clearance Scoring

Outer clearance scoring evaluates whether key rooms maintain sufficient distance from the outer walls or from the floor boundary. The intent is to avoid extreme placements that would make rooms inaccessible or create sharp interior corners.

This score also behaves smoothly. A candidate close to the boundary suffers a moderate penalty, while one further inside receives a higher reward. This incentivizes balanced layouts rather than just viability.

#### 3.4.3.3 Room Relation Scoring

Room relation scoring uses the database-derived adjacency graph. It scores candidate layouts based on how well related rooms belong near one another.

The relation constraints can represent adjacency, connectivity, or directional preferences. The scoring function evaluates pairwise distances and penalizes crossing relations or distant room pairings. It can also reward alignment consistent with the template’s intended circulation.

These relation scores are dynamic: the same module adapts its penalty scale depending on the active room template and the number of related rooms.

#### 3.4.3.4 Smooth Scoring vs Boolean Flags

A central design decision is the use of smooth scoring functions rather than Boolean constraint flags. Boolean scoring would classify candidate layouts as simply valid or invalid, leading to an extremely rugged optimization surface. Instead, smooth scores assign partial credit based on how closely a layout satisfies each criterion.

This approach allows Optuna to learn from suboptimal proposals. Even a poor layout can contribute useful gradient information, guiding the search gradually toward higher-quality regions.

In this system, the Optuna objective is not a pure feasibility signal. It is partitioned so that approximately 90% of the score comes from spatial and relational quality, while the remaining 10% accounts for whether the candidate is even likely to generate a valid floor plan.

This weighting reflects the pipeline’s two-stage philosophy: first find good hint placement, then use a solver to convert the hints into a concrete plan.

### 3.4.4 Floor Plan Generation Process

Once Optuna has identified a strong hint map, the system initiates the actual floor plan generation task. The hint map is passed to a solver-based floor plan generator that attempts to realize the layout within hard constraint bounds.

#### 3.4.4.1 Initial Generation with Hints

The solver performs the first generation phase using the hint map as a seed. During this phase, the layout is constructed primarily according to hard constraints.

Hard constraints include:

- room dimension bounds (minimum and maximum width/height),
- non-overlap and rectilinear adjacency constraints,
- boundary containment within the validated floor envelope,
- mandatory room connectivity and circulation requirements.

These constraints ensure that the output plan is structurally valid. The solver uses the hint positions to bias room placement while still respecting the exact geometry requirements.

The system is designed to be compatible with various room templates. Hard constraints are expressed in an abstract manner so that they can adapt to multiple room types rather than assuming a single fixed layout. For example, the same adjacency constraint mechanism can support bedroom-to-bathroom relationships in one template and living-room-to-kitchen relationships in another.

#### 3.4.4.2 Multiple Attempts per Hint Map

The methodology allows repeated solver runs for the same hint map. This is intentional because the solver may require several attempts to find a valid instantiation even from a promising skeleton.

Repeated attempts help in several ways:

- they overcome nondeterministic solver behavior,
- they allow the system to explore different interpretations of the same hint geometry,
- they increase the chance of escaping local infeasibility caused by incidental room overlaps.

The repeated runs are usually bounded by a small count, preserving performance while improving robustness.

#### 3.4.4.3 Hard Constraints and Layout Compatibility

Hard constraints are grouped into logical categories rather than hard-coded room pairs. This means the system can represent:

- perimeter containment constraints for any room,
- mutual exclusion between all pairs of affected rooms,
- relational adjacency constraints for any connected room types.

This compatibility is important for generating layouts across different templates, from simple apartment units to more complex multi-room houses.

### 3.4.5 Refinement Stage

If the initial solver run is feasible, the system enters a refinement stage. This stage treats the initial floor plan as a seed and makes small, incremental adjustments to improve soft quality metrics.

The refinement process is guided by soft constraints, while hard constraints remain enforced to prevent invalid plans.

#### 3.4.5.1 Soft Constraints in Refinement

Soft constraints in the refiner include:

- improved adjacency and circulation,
- smoother room shapes and aspect ratios,
- better use of remaining free space,
- reduction of interior gaps.

These constraints are not absolute requirements. Instead, they act as optimization targets that the refiner attempts to satisfy without violating the hard constraints.

#### 3.4.5.2 Hard Constraints During Refinement

During refinement, hard constraints are still enforced. This means that even though the plan is being tweaked for quality, it cannot drift into invalid configurations.

The refiner ensures that room sizes and boundary containment remain intact. It also preserves non-overlap and essential connectivity constraints.

#### 3.4.5.3 Movement Restriction and Search Space Reduction

A key design decision in the refinement stage is to restrict the adjustment magnitude per step. Instead of allowing large resizes or repositioning, the refiner limits changes to subtle movements and incremental dimension shifts.

This restriction has two benefits:

- it keeps the search space small, which makes each refinement iteration efficient,
- it prevents drastic changes that could discard the valid structure already obtained.

The refiner effectively performs a local search around the initial feasible plan. It leverages the fact that a valid layout is already available, so only minor corrections are needed to enhance quality.

### 3.4.6 Floor Plan Post Processing

Even with solver-based generation and refinement, the resulting plans can contain undesirable topologies. Common issues include internal air gaps, inward pockets, and dangling spaces that are technically feasible but not usable.

To address this, the system applies a final post-processing step.

#### 3.4.6.1 The Need for Post Processing

The core solver uses a constraint programming approach. While powerful, this solver can produce solutions that satisfy all explicit constraints but still leave interior gaps or concave pockets because those issues are not easily expressed as linear constraints.

The post-processing stage is therefore designed as a last corrective pass. It targets geometry problems that are outside the solver’s primary scope.

#### 3.4.6.2 Post Processing Features

The post processor includes several repair mechanisms:

- gap filling to remove internal air pockets,
- edge adjustment to eliminate inward protrusions,
- wall extension and snapping to regularize rectilinear boundaries,
- veranda layout modification for exterior space consistency.

Each feature operates at a geometric level. The process inspects the current room polygons, identifies problematic shapes, and applies local modifications that preserve the core plan while improving usability.

For example, inward pockets are corrected by pushing neighboring room boundaries outward or by merging small empty zones with adjacent rooms. Wall extension fills narrow notches that would otherwise create unusable circulation paths.

This post-processing stage is particularly important because it can rescue plans that would otherwise be rejected by a downstream scoring system.

### 3.4.7 Floor Plan Scoring

The final scoring step evaluates the generated floor plan against a set of quality metrics.

The scoring logic is hierarchical. It begins with hard verification of the plan geometry and proceeds to more nuanced quality measures.

Key scoring dimensions include:

- geometric validity and rectilinearity,
- conformity to room dimension and adjacency constraints,
- spatial coverage efficiency,
- outer clearance and zone appropriateness,
- coherence with the original requirement template.

The scoring function is designed to reward plans that are not only valid but also architecturally sensible. For example, a plan that satisfies all hard constraints but places the living room in a remote corner would receive a lower score than one that also respects expected circulation.

The score is used both internally and externally. Internally, it can influence whether a plan is considered a candidate for final delivery. Externally, it can be included in the response payload as a quality indicator.

## 3.5 Final Results Delivery

The final stage is delivery to the client. The system packages the selected floor plan, the scoring summary, and any relevant metadata into a normalized response structure.

The method ensures that the client receives only plans that passed both structural validation and quality assessment. Plans that fail the post-processing or scoring thresholds are filtered out and reported with explanatory messages.

This delivery mechanism supports the following goals:

- transparency: the client can see why a plan was accepted or rejected,
- reliability: only vetted plans are returned,
- extensibility: future client interfaces can render the plan geometry and score independently.

## 3.6 Summary

The methodology of this floor plan generator emphasizes a staged, data-driven pipeline. It begins with physical land feasibility, continues through rigorous requirement construction and bounded optimization, and concludes with solver-based generation plus post-hoc repair.

The most important methodological contributions are:

- reduction of search space through validated floor bounds,
- use of Optuna as a room-hint recommendation engine rather than a full layout solver,
- smooth, continuous scoring to guide trial exploration,
- separation of hard and soft constraints across generation and refinement,
- a repair-oriented post-processing stage to address geometric defects.

This architecture makes the generator robust against infeasible inputs and capable of producing usable floor plans from complex requirements.

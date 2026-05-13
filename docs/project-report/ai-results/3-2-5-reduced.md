## Chapter 3.2.5 Constraint-Based Floor Plan Generation Framework

The floor plan generator is the computational core of the project. It converts architectural requirements into feasible rectangular room arrangements while satisfying geometric, functional, and stylistic constraints. This stage is computationally demanding because the system must preserve feasibility while supporting multiple valid architectural interpretations.
The generator is implemented as a constraint programming model solved through a CP-SAT framework. Floor planning is treated as a combinatorial placement problem governed by exact relational conditions rather than continuous optimization alone. Rooms must avoid overlap, preserve adjacency relationships, maintain frontage order, and remain spatially coherent. The solver therefore balances strict admissibility with guided exploration.
The coordinate system defines the interpretation of spatial rules. The origin is positioned at the bottom-left corner of the floor plate, the horizontal axis extends left to right, and the vertical axis represents depth from frontage toward the interior. Under this convention, (y = 0) denotes the front boundary of the plan. This directional interpretation is important because several rules depend directly on frontage alignment, entrance depth, and exterior positioning.
The generation process is divided into two operational profiles. The first profile produces an initial feasible arrangement from requirement data, while the second profile refines an existing arrangement through bounded optimization. This staged structure prevents unnecessary modification of previously acceptable layouts and separates feasibility establishment from qualitative improvement.
The configuration interface functions as a constraint-selection mechanism that enables or disables rule groups without altering the solver architecture. As a result, different operational modes are produced through configuration changes rather than separate generation systems.

### Computational Core and Solver Logic

The computational engine constructs the constraint model, creates decision variables for each room, applies the selected constraints, and instructs the solver to search for feasible or improved arrangements. Each room is represented as a constrained rectangle with explicit positional and dimensional variables.
Initialization begins by normalizing requirement data and preparing the room set for optimization. The process also introduces automatically generated spaces, such as circulation areas and primary living regions, allowing the solver to reason over the complete spatial topology rather than only user-defined rooms.
For every room, the model defines variables representing left and bottom coordinates, width, height, right and upper boundaries, and total area. These values are linked through exact arithmetic relationships to preserve internal geometric consistency. Rectangular abstraction simplifies the optimization process while still enabling complex spatial reasoning.
Constraints are introduced progressively. Geometric feasibility is established first, followed by architectural rules governing adjacency, circulation, frontage behavior, shared boundaries, and room-specific placement conditions. Soft optimization objectives are then applied when refinement-oriented configurations are enabled. This ordering ensures that admissibility is secured before qualitative optimization occurs.
The solver operates within bounded execution time and incorporates randomized search behavior. Time limitations prevent excessive computation, while randomized exploration increases layout diversity. This is important because floor planning rarely has a single universally optimal arrangement; instead, multiple acceptable solutions may satisfy the same architectural requirements.
The optimization objective is expressed as a weighted aggregation of active soft penalties:

[
\min \sum_{k=1}^{n} \lambda_k C_k
]

where (C_k) represents an individual soft-cost component and (\lambda_k) represents its corresponding weight. When no soft terms are enabled, the solver performs a pure feasibility search.

### Phase I: Feasibility-Driven Synthesis

The initialization profile generates a new layout directly from requirement specifications. Its primary objective is to establish a structurally valid baseline rather than a fully refined arrangement. Consequently, this profile emphasizes hard feasibility constraints and only limited soft guidance.
The profile employs point-based positional hints that provide the solver with approximate spatial tendencies derived from the input requirements. These hints are not rigid geometric commitments; instead, they guide the solver toward promising regions of the search space while still allowing alternative placements when necessary.
The generation phase prioritizes essential validity conditions. The produced layout must satisfy non-overlap conditions, geometric consistency, frontage ordering, and mandatory adjacency relationships before aesthetic refinement is considered. This reflects the architectural principle that spatial admissibility precedes stylistic optimization.
The initialization stage intentionally minimizes dependence on seed-based penalties. Excessive attachment to prior arrangements during early synthesis could restrict exploration and prevent discovery of feasible baseline layouts. The profile therefore preserves broad search freedom within the legal design envelope.

### Phase II: Iterative Layout Refinement

The refinement profile operates on an existing feasible layout and attempts to improve it without significantly altering its overall composition. This process functions as a localized optimization strategy in which the solver searches for improved variants near the current arrangement.
Its defining feature is bounded movement. Rooms are permitted only limited positional deviation from their prior state, ensuring that the refined output remains recognizably related to the original configuration. This behavior supports iterative architectural development, where successive passes gradually improve a design rather than replacing it entirely.
Unlike initialization, refinement introduces a richer set of soft preferences. These preferences do not invalidate solutions but influence the ranking of candidate layouts. The solver is encouraged to preserve alignments, improve shared-wall organization, reduce wasted space, and maintain frontage clarity.
The refinement stage may be applied repeatedly. Each iteration can improve different aspects of the arrangement, such as compactness, facade organization, or circulation quality. This layered optimization strategy enables progressive enhancement without requiring separate algorithms for each architectural objective.
The refinement process also demonstrates an important system principle: constraint significance varies by stage. Feasibility dominates during initial synthesis, whereas descriptive architectural preferences become more influential during refinement. This staged methodology reduces overconstraint during early search and improves interpretability of the resulting layouts.

### Constraint Formalization and Taxonomy

The constraint architecture translates architectural intent into mathematical form. The system follows a two-tier taxonomy composed of hard constraints and soft constraints. Hard constraints define non-negotiable feasibility conditions, while soft constraints express qualitative preferences among otherwise valid layouts.

#### Hard Constraints

Hard constraints establish structural admissibility. They ensure geometric consistency, directional order, functional connectivity, and architectural plausibility.

##### Geometric Feasibility and Rectangular Consistency

Geometric feasibility constraints prevent room overlap and preserve consistency between positional and dimensional variables. Aspect-ratio limitations also restrict excessively narrow or flattened room geometries.
These rules form the foundation of the entire model because higher-level reasoning depends on reliable geometric definitions. Without stable room boundaries, adjacency and frontage relationships cannot be evaluated meaningfully.
Certain room categories receive differentiated proportional tolerances. For example, garages and verandas may adopt more elongated forms than standard enclosed spaces, improving practical realism.

##### Circulation Spine Morphology and Connectivity

Circulation constraints ensure that hallway-like regions maintain recognizable passage characteristics. A hallway must preserve a narrow dimension within controlled bounds while maintaining sufficient longitudinal extension.
Connectivity requirements ensure that circulation areas interact with principal living spaces and at least one additional functional room. This prevents isolated or non-functional passage regions.
The system also evaluates boundary-sharing behavior. Hallways are expected to share meaningful wall segments with neighboring rooms, encouraging integration into the overall composition.

##### Boundary Coupling and Enclosure Requirements

Boundary-coupling constraints regulate how strongly rooms participate in the enclosing structure of the plan. Different room categories may specify minimum and maximum expectations for fully shared boundaries.
A controlled tolerance margin may be applied to allow near-complete alignments when overlap remains sufficiently close to the intended threshold. This improves robustness while preserving spatial precision.
Rooms with stronger enclosure expectations generally occupy deeper interior positions, while rooms with weaker requirements may remain closer to the exterior perimeter.

##### Mandatory Functional Adjacency

Functional adjacency constraints enforce indispensable spatial relationships between room categories. The solver distinguishes between direct mandatory adjacency and alternative permissible adjacency groups.
Adjacency evaluation is not based solely on point contact. A minimum overlap threshold is required to ensure that shared boundaries represent meaningful architectural relationships rather than incidental geometric coincidence.
These constraints define the functional communication graph of the house and prevent impractical separation between related spaces.

##### Front-to-Back Spatial Hierarchy

Front-to-back hierarchy introduces directional organization into the plan. Frontage-associated spaces must remain closer to the exterior boundary than deeper interior rooms. When a veranda exists, it acts as the primary frontage anchor; otherwise, the living area assumes this role.
This rule prevents inversion of frontage semantics and reinforces the interpretation of the house as a depth-oriented spatial sequence progressing from public entry to private interior.

##### Frontage Interface Regulation

Frontage interface regulation governs the veranda as a transition zone between interior and exterior space. The veranda is anchored to the front boundary and associated with a reserved outdoor region that does not overlap other rooms.
This treatment transforms the frontage from a simple boundary line into a structured architectural interface.

##### Vehicular Annex Placement and Access

Garage placement constraints regulate both orientation and accessibility. The garage must align with exactly one lateral boundary, preventing ambiguous central placement.
Accessibility requirements further ensure that the garage either connects directly to the frontage or receives aligned access through the frontage region.

##### Perimeter Staggering and Setback Regulation

Perimeter staggering introduces controlled variation into the external outline of the plan. Rather than enforcing a perfectly flush perimeter, the solver encourages selective setbacks and stepped boundary behavior.
This produces a more varied building outline while preserving geometric coherence.

##### Service-Side Clearance Preservation

Service-side clearance constraints preserve usable setback space behind selected kitchen or circulation walls. The model verifies that sufficient unobstructed depth exists beyond these walls to maintain practical movement and access conditions.
Unlike a global setback rule, this mechanism applies only to functionally sensitive regions.

#### Soft Constraints

Soft constraints shape the preference landscape of the solver without determining admissibility. These objectives are particularly important during refinement because they improve architectural quality while preserving feasibility.

##### Adjacency Affinity Preference

Adjacency affinity extends mandatory adjacency logic into a preference-based form. Desired relationships improve the ranking of candidate layouts even when they are not strictly required.

##### Plan Compactness and Centrality

Compactness objectives encourage rooms to remain near the horizontal center of the floor plate while preserving balanced front-to-back organization. The objective discourages excessive lateral dispersion and promotes coherent clustering.

##### Residual Void Minimization

Residual void minimization penalizes inefficient unused area inside the bounding envelope of the layout. If (A\_{bbox}) represents the area of the enclosing rectangle and (\sum_i A_i) represents the total room area, the residual void is expressed as:

[
D = A_{bbox} - \sum_i A_i
]

Minimizing (D) encourages efficient occupancy of the shared envelope and reduces fragmented empty regions.

##### Seed-Conditioned Positional Guidance

Seed-conditioned guidance transfers information from an existing layout into the refinement process. Suggested room positions and dimensions bias the solver toward preserving prior organizational structure while still permitting bounded adjustment.
This mechanism is particularly important during iterative refinement because it maintains continuity between successive design stages.

##### Facade Depth Conservation

Facade depth conservation preserves the prominence of rooms previously aligned with the frontage boundary. Excessive inward displacement from the facade line is penalized to maintain frontage clarity and exterior ordering.

##### Boundary Alignment Conservation

Boundary alignment conservation preserves meaningful edge alignments inherited from seed layouts. When rooms previously exhibited coherent alignment relationships, deviations from those relationships increase optimization cost.
This mechanism supports architectural legibility, particularly along visible facade regions.

##### Recess Modulation of the Frontage Plane

Recess modulation evaluates the severity and context of frontage recesses. Moderate recesses may be tolerated, while excessive inward displacement receives stronger penalties.
The rule also considers nearby attachment relationships to preserve facade rhythm and proportional consistency.

##### Boundary-Coupling Reinforcement

Boundary-coupling reinforcement transforms enclosure expectations into graded optimization targets during refinement. Instead of invalidating solutions that fail to meet stronger shared-wall preferences, the solver assigns proportional penalties.
This demonstrates stage-sensitive optimization behavior: conditions that define feasibility during generation become quality metrics during refinement.

### End of This Chapter

The floor plan generator represents the most structurally demanding component of the project because it integrates geometry, functionality, and architectural intent within a unified optimization framework. Its effectiveness arises from the coordinated interaction between hard feasibility constraints, staged refinement, and soft qualitative objectives.
The initialization profile establishes a valid spatial foundation, while the refinement profile incrementally improves architectural quality through bounded adjustment. Together, these processes enable the generation of layouts that are both feasible and architecturally coherent.
The chapter demonstrates that floor planning extends beyond simple geometric arrangement. It requires the translation of architectural meaning into formal mathematical constraints and the controlled exploration of admissible spatial configurations. By combining strict geometric legality with configurable spatial intelligence, the generator functions as the conceptual center of the overall system.

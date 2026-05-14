Constraint Formalization and Taxonomy
The constraint architecture translates architectural intent into mathematical form. The system follows a two-tier taxonomy composed of hard constraints and soft constraints. Hard constraints define non-negotiable feasibility conditions, while soft constraints express qualitative preferences among otherwise valid layouts.

#### Hard Constraints

Hard constraints establish structural admissibility. They ensure geometric consistency, directional order, functional connectivity, and architectural plausibility.
Geometric Feasibility and Rectangular Consistency
Geometric feasibility constraints prevent room overlap and preserve consistency between positional and dimensional variables. Aspect-ratio limitations also restrict excessively narrow or flattened room geometries.
These rules form the foundation of the entire model because higher-level reasoning depends on reliable geometric definitions. Without stable room boundaries, adjacency and frontage relationships cannot be evaluated meaningfully.
Certain room categories receive differentiated proportional tolerances. For example, garages and verandas may adopt more elongated forms than standard enclosed spaces, improving practical realism.
Circulation Spine Morphology and Connectivity
Circulation constraints ensure that hallway-like regions maintain recognizable passage characteristics. A hallway must preserve a narrow dimension within controlled bounds while maintaining sufficient longitudinal extension.
Connectivity requirements ensure that circulation areas interact with principal living spaces and at least one additional functional room. This prevents isolated or non-functional passage regions.
The system also evaluates boundary-sharing behavior. Hallways are expected to share meaningful wall segments with neighboring rooms, encouraging integration into the overall composition.
Boundary Coupling and Enclosure Requirements
Boundary-coupling constraints regulate how strongly rooms participate in the enclosing structure of the plan. Different room categories may specify minimum and maximum expectations for fully shared boundaries.
A controlled tolerance margin may be applied to allow near-complete alignments when overlap remains sufficiently close to the intended threshold. This improves robustness while preserving spatial precision.
Rooms with stronger enclosure expectations generally occupy deeper interior positions, while rooms with weaker requirements may remain closer to the exterior perimeter.
Mandatory Functional Adjacency
Functional adjacency constraints enforce indispensable spatial relationships between room categories. The solver distinguishes between direct mandatory adjacency and alternative permissible adjacency groups.
Adjacency evaluation is not based solely on point contact. A minimum overlap threshold is required to ensure that shared boundaries represent meaningful architectural relationships rather than incidental geometric coincidence.
These constraints define the functional communication graph of the house and prevent impractical separation between related spaces.
Front-to-Back Spatial Hierarchy
Front-to-back hierarchy introduces directional organization into the plan. Frontage-associated spaces must remain closer to the exterior boundary than deeper interior rooms. When a veranda exists, it acts as the primary frontage anchor; otherwise, the living area assumes this role.
This rule prevents inversion of frontage semantics and reinforces the interpretation of the house as a depth-oriented spatial sequence progressing from public entry to private interior.
Frontage Interface Regulation
Frontage interface regulation governs the veranda as a transition zone between interior and exterior space. The veranda is anchored to the front boundary and associated with a reserved outdoor region that does not overlap other rooms.
This treatment transforms the frontage from a simple boundary line into a structured architectural interface.
Vehicular Annex Placement and Access
Garage placement constraints regulate both orientation and accessibility. The garage must align with exactly one lateral boundary, preventing ambiguous central placement.
Accessibility requirements further ensure that the garage either connects directly to the frontage or receives aligned access through the frontage region.
Perimeter Staggering and Setback Regulation
Perimeter staggering introduces controlled variation into the external outline of the plan. Rather than enforcing a perfectly flush perimeter, the solver encourages selective setbacks and stepped boundary behavior.
This produces a more varied building outline while preserving geometric coherence.
Service-Side Clearance Preservation
Service-side clearance constraints preserve usable setback space behind selected kitchen or circulation walls. The model verifies that sufficient unobstructed depth exists beyond these walls to maintain practical movement and access conditions.
Unlike a global setback rule, this mechanism applies only to functionally sensitive regions.

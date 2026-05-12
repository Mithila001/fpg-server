### Chapter 4.2.5 Constraint-Based Floor Plan Generation Framework

The floor plan generator constitutes the computational core of the project. It is the stage in which architectural intent is translated into a spatially feasible arrangement of rectangular rooms under a dense set of geometric, relational, and stylistic requirements. Among all components of the system, this stage consumes the greatest amount of computational effort because it must simultaneously satisfy hard feasibility conditions, preserve design intent, and retain enough freedom to produce diverse layouts.

At a conceptual level, the generator is built upon a constraint programming model solved through a CP-SAT engine. This choice is appropriate because floor planning is not merely a matter of optimization in the usual continuous sense; it is a combinatorial placement problem governed by exact relational rules. Rooms must not overlap, required adjacencies must be honored, frontage rules must be preserved, and the resulting arrangement must still remain adaptable enough to accommodate multiple viable architectural interpretations. The solver therefore operates as a balance between strict admissibility and guided exploration.

The coordinate system is significant for the interpretation of every rule. The origin lies at the bottom-left of the floor plate, the horizontal axis extends from left to right, and the vertical axis expresses depth from the frontage toward the interior. In this orientation, $y=0$ corresponds to the front edge of the plan. This convention is essential because several constraints reason directly about entrance depth, frontage preservation, and the placement of rooms that should remain near the exterior boundary. As a result, geometric optimization is not abstractly symmetric; it is semantically directional.

The generation pipeline is organized into profiles. The primary generation profile focuses on producing a fresh, feasible layout from a requirement set. The refinement profile, by contrast, accepts an existing layout and attempts to improve it through a bounded re-solve that preserves the overall composition while adjusting local spatial relationships. This staged structure is one of the most important architectural decisions in the system, because it prevents the solver from treating all layouts as if they were equally free to change. Instead, each pass carries a distinct objective: first feasibility, then controlled improvement.

The configuration panel acts as a constraint selection matrix. It allows the system to enable or disable individual families of rules without altering the underlying solver architecture. This makes the generator both experimentally flexible and analytically transparent. Different profiles are therefore not separate solvers in the strict sense, but rather different configurations of the same spatial reasoning engine.

#### Computational Core and Solver Logic

The core engine is responsible for assembling the full constraint model, declaring the decision variables for every room, injecting the selected rules, and instructing the solver to search for a feasible or improved arrangement. Its role is foundational: before any optimization can occur, every room must be represented as a rectangle with explicit position, size, and boundary variables. The model then interprets the entire plan as a coupled system of integer decisions.

Initialization begins by normalizing the requirement data and preparing the room set for solver use. The process does not merely read room descriptors; it also incorporates system-generated rooms that arise from architectural logic, such as the living area and any required circulation elements. This is important because the floor plan is not assembled only from user-specified rooms. It is a structured composition in which certain anchor spaces are introduced automatically so that the solver can reason over the complete plan topology.

For each room, the engine creates decision variables representing the left coordinate, bottom coordinate, width, height, right boundary, upper boundary, and area. These variables are linked by exact arithmetic relations so that the rectangle remains internally consistent. In effect, every room becomes a constrained geometric object rather than a free-form polygon. The use of rectangular decision variables is a deliberate simplification that makes the problem computationally tractable while still supporting rich spatial reasoning.

The core engine then applies constraints in a layered sequence. First, it establishes the most fundamental geometric feasibility conditions. Next, it introduces domain-specific rules governing hallways, shared walls, required adjacencies, frontage anchors, and special placement behavior for key rooms. Finally, it adds objective terms when a refinement-oriented or soft-guided configuration is active. This order matters because hard feasibility must be secured before the solver can meaningfully evaluate softer preferences.

The solver itself is deliberately randomized within bounded time. A time cap prevents the system from spending unbounded effort on a single layout, while randomized search parameters encourage diversity across repeated runs. This design is especially valuable in floor planning, where multiple plausible solutions may exist and the goal is not always a single mathematically optimal arrangement, but rather a strong compromise between feasibility, usability, and architectural character.

The final objective is assembled as a weighted sum of the active soft penalties:

$$
\min \sum_{k=1}^{n} \lambda_k C_k
$$

where each $C_k$ is a soft cost component and $\lambda_k$ is its corresponding weight. If no soft terms are enabled, the solver performs a pure feasibility search. Otherwise, it seeks layouts that satisfy all hard requirements while minimizing the combined soft cost.

#### Phase I: Feasibility-Driven Synthesis

The initialization profile is designed to build a fresh floor plan from requirement data. Its conceptual purpose is not to polish an existing arrangement, but to establish a valid structural baseline. In practical terms, this profile emphasizes hard feasibility and only a minimal set of soft biases. This makes it the most conservative profile in the system and the one most closely aligned with first-pass generation.

A notable feature of this profile is the use of point-based hints to derive an initial spatial tendency. These hints are not equivalent to hard geometric commitments. Rather, they provide the solver with a plausible starting direction derived from the input requirements. This helps the system begin the search within a relevant region of the solution space, while still allowing the engine to explore alternatives when necessary. In this sense, the hints serve as initialization guidance rather than as rigid design locks.

The initialization profile is intentionally focused on enforcing hard conditions that are necessary for validity. The generated layout must respect non-overlap, room shape limits, adjacency logic, and frontage semantics before any stylistic concerns are considered. This reflects a common architectural principle: a plan must first be admissible before it can be aesthetically refined.

Because the generation profile is meant to establish the first workable layout, it typically avoids heavy dependence on seed-based penalties. That separation is important. If the first pass were overly constrained by prior arrangement logic, it could fail to discover a legitimate baseline in the first place. The profile therefore prioritizes feasibility, structural coherence, and broad search freedom within the legal design envelope.

#### Phase II: Iterative Layout Refinement

The refinement profile represents the second major phase of the generator. Whereas the initialization profile seeks a valid arrangement from scratch, the refinement profile assumes that a layout already exists and attempts to improve it without destroying its overall structure. This is a classic local-search strategy: the system reuses an existing solution as context and asks the solver to produce a better nearby variant.

The distinctive feature of refinement is bounded movement. Rather than permitting unrestricted repositioning, the solver is given a limited spatial wiggle around the prior solution. This ensures that the resulting output remains recognizably related to the original plan. Such bounded adjustment is especially useful when the goal is iterative design development, where each pass should polish the composition rather than replace it wholesale.

The refinement profile also introduces a richer set of soft preferences. These preferences do not block feasibility, but they do reshape the ranking of candidate layouts. As a result, the solver is encouraged to preserve useful alignments, reduce wasted area, maintain facade clarity, and improve the quality of shared walls. The profile is therefore less about simply satisfying constraints and more about increasing the architectural maturity of an already viable plan.

Conceptually, the refinement process can be applied more than once. Each pass may receive the output of the previous pass, creating a multi-stage improvement sequence. This is valuable because certain spatial qualities emerge only gradually. A first refinement may recover structure; a second may improve compactness; a third may sharpen facade order. The architecture of the solver supports this layered improvement model without requiring a distinct algorithm for each pass.

The refinement profile also reveals an important philosophy of the system: not all constraints should be treated equally in every phase. Early in the process, feasibility dominates. Later, a richer set of descriptive preferences can be brought into play. This staged approach reduces the risk of overconstraining the solver too soon and improves the interpretability of the final output.

#### Constraint Formalization and Taxonomy

The constraint system constitutes the primary mechanism through which architectural intent is translated into an admissible spatial configuration. For analytical clarity, the model is best understood as a two-tier taxonomy. Hard constraints establish feasibility and define the non-negotiable spatial envelope. Soft constraints, by contrast, operate as preference terms that influence ranking among otherwise valid candidates. The distinction is essential: a violation of a hard constraint renders a plan invalid, whereas a violation of a soft constraint merely reduces its desirability.

The following discussion excludes auxiliary extender behavior, since that pathway belongs to a separate architectural branch and is not part of the main generation and refinement narrative in this chapter.

##### Hard Constraints

The hard constraint family is responsible for structural admissibility. It ensures that rooms remain geometrically consistent, functionally connected, and directionally ordered in a manner compatible with residential planning conventions. Collectively, these rules prevent the solver from producing arrangements that are mathematically possible but architecturally incoherent.

###### Geometric Feasibility and Rectangular Consistency

Geometric feasibility rules establish the lowest level of validity. They prevent overlap, preserve coordinate consistency, and ensure that each room’s boundary values remain internally coherent with its declared position and dimensions. In addition, aspect-ratio bounds constrain the width-to-height relation so that excessively thin or flattened shapes do not appear under ordinary conditions.

This family is foundational because every subsequent rule depends on a reliable notion of spatial extent. If two rooms are allowed to intersect, or if a room can violate its own boundary logic, then adjacency and frontage reasoning lose interpretive value. The model must first establish where each room begins and ends before it can evaluate higher-order relationships.

Certain room types are granted differentiated proportional tolerance because their functional geometry departs from that of conventional interior spaces. Garages and verandas, for example, may justifiably exhibit more elongated proportions than a standard enclosed room. This is not merely a cosmetic choice; it prevents the solver from generating layouts that are mathematically admissible but practically implausible.

###### Circulation Spine Morphology and Connectivity

Circulation constraints ensure that hall-like spaces behave as genuine passage elements rather than arbitrary rectangular fillers. A hallway must preserve a narrow dimension within a controlled range and a sufficiently extended complementary dimension so that its linear character remains legible.

Connectivity is equally important. The circulation space is expected to connect with the principal living area and at least one additional non-living room, either directly or through a controlled chain of similar spaces. This requirement prevents circulation from becoming isolated or functionally inert. The hallway therefore operates as connective tissue within the spatial organization of the house.

The rule set further evaluates boundary-sharing behavior. A hallway should retain a minimum number of fully shared sides with neighboring rooms, encouraging integration into the overall composition rather than floating as an isolated void. From an architectural perspective, this improves both readability and use-value.

###### Boundary Coupling and Enclosure Requirements

Boundary-coupling rules regulate how strongly a room participates in the enclosing fabric of the plan. Rather than treating all rooms as equally exposed, the model allows each room category to express its own expectations regarding the number of sides that should be fully shared with adjacent spaces. This is particularly useful for distinguishing public, private, and transitional zones.

The hard version of this rule counts the number of fully shared sides and verifies that the selected sides satisfy type-specific minimum and maximum thresholds. A controlled relaxation margin may be admitted through a wiggle percentage, allowing the solver to accept near-complete alignments when the coverage is sufficiently close. This preserves robustness without sacrificing precision.

Beyond adjacency in the narrow sense, this family influences whether a room feels embedded within the plan or exposed at its margins. Rooms with stronger boundary-coupling requirements tend to occupy deeper positions in the arrangement, whereas rooms with looser requirements may remain nearer to the perimeter. The result is a subtle but meaningful spatial hierarchy.

###### Mandatory Functional Adjacency

Functional adjacency rules are derived from relation data that expresses indispensable connections between room categories. The solver distinguishes between direct mandatory relations and broader alternative relations. In the former case, a room must adjoin one or more specified targets; in the latter, adjacency may be satisfied by any compatible member of a permitted set.

This relation is not a simple yes-or-no touch condition. It also incorporates a minimum overlap threshold so that accidental point contact is not mistaken for meaningful adjacency. Such a threshold is necessary because functional relationships in residential planning typically require a substantial shared boundary rather than a negligible geometric coincidence.

These rules define the functional graph of the house. They determine which rooms can plausibly communicate and which separations would be excessive. In this sense, adjacency constraints often influence the lived logic of the plan more strongly than its visual appearance.

###### Front-to-Back Spatial Hierarchy

Front-to-back spatial hierarchy introduces a macro-level directional order into the plan. The frontage side is treated as the front of the house, and spaces that mediate that frontage must remain closer to the exterior edge than deeper interior rooms. When a veranda exists, it becomes the primary anchor; otherwise, the living area serves that role.

This rule is important because it prevents the frontage logic from becoming inverted or ambiguous. The plan should not be understood as an undifferentiated set of adjacent rooms; it should express a depth hierarchy that moves from public entry toward private interior. The rule enforces that hierarchy through geometric comparison of room centers.

Its effect is subtle but consequential. By stabilizing the front-to-back ordering, the model reduces symmetry-induced drift and strengthens the legibility of the whole arrangement. It is therefore a structural semantic rule rather than a purely local geometric one.

###### Frontage Interface Regulation

Frontage interface regulation governs the veranda as a mediator between the house and the exterior. The veranda is fixed to the front boundary so that it clearly articulates the relationship between interior occupation and external access. In addition, the model creates an auxiliary outdoor-space region associated with the veranda, which preserves the intended frontage composition.

The veranda must attach along one side to this outdoor region, and the region itself is positioned so that it does not overlap with other actual rooms. The frontage is therefore not treated as an abstract line but as a structured interface with reserved geometry. The veranda consequently functions as a frontage organizer rather than as a mere room category.

This rule family is especially valuable because it protects a highly recognizable architectural feature from being absorbed into the general room pool. It ensures that the front edge of the plan retains a clear civic and spatial identity.

###### Vehicular Annex Placement and Access

Vehicular annex placement regulates the garage through both anchoring and access logic. The garage must lie near exactly one lateral boundary, either left or right, which establishes a clear vehicular orientation and avoids ambiguous central placement.

Access is equally important. The garage must either sit directly on the front boundary or receive access through an aligned frontage segment. In this way, the garage is not only geometrically attached to the boundary but also functionally reachable in a manner consistent with practical use. The rule therefore combines placement logic with circulation semantics.

This constraint has a significant effect on feasibility because the garage occupies a specialized role within frontage composition. If other hard rules already crowd the front edge, the garage may become difficult to place. Rather than indicating a defect, this difficulty reflects the solver’s negotiation of a realistic architectural tradeoff.

###### Perimeter Staggering and Setback Regulation

Perimeter staggering shapes the outer massing of the plan by encouraging controlled setback behavior along selected exterior sides. Instead of permitting every room to align flush with the envelope, the solver is guided toward stepped edges with deliberate offsets. The resulting outline is more articulated and less monotonic.

The rule rests on the principle that rooms exposed to the exterior should maintain a positive clearance relationship with neighboring rooms along designated sides. The outcome is not a rigid perimeter polygon in the conventional sense, but a sequence of controlled displacements that introduce architectural variation into the outline.

Because it affects both spatial placement and visual rhythm, this regulation influences form as much as function. It therefore occupies an important position in the overall massing strategy.

###### Service-Side Clearance Preservation

Service-side clearance preservation requires at least one eligible kitchen or circulation back wall to retain a clear setback behind it. The purpose is to avoid placing a functional rear wall too close to the interior boundary, where door clearance and movement depth may become inadequate.

The rule examines the distance from the relevant back wall to the floor boundary and checks whether the adjacent zone remains free from intrusive room geometry. This creates a protected depth band that improves usability. It is therefore a targeted regulation rather than a blanket setback rule.

Its significance lies in its attention to practical circulation quality. Certain room types require a comfortable rear-wall buffer, and this rule protects that requirement without imposing an unnecessary restriction on the remainder of the plan.

##### Soft Constraints

Soft constraints do not determine admissibility; instead, they shape the solver’s preference landscape. They guide the search toward layouts that are not only valid but also compositionally refined, spatially compact, and semantically legible. In practice, these terms are especially important during refinement, where the goal is to improve an already feasible arrangement without destroying its structural identity.

###### Adjacency Affinity Preference

Adjacency affinity uses the same relational logic as the mandatory adjacency family, but it translates the result into a preference signal rather than a feasibility requirement. The solver can therefore benefit from the adjacency information without being constrained to a narrow set of exact placements.

This mechanism preserves flexibility. Its practical contribution may depend on the extent to which the preference variables are integrated into the active objective, but conceptually it still matters because it defines a candidate adjacency field for later scoring.

###### Plan Compactness and Centrality

The compactness objective encourages rooms to remain near the horizontal center of the floor plate while also biasing the arrangement toward the front-oriented side of the coordinate frame. Mathematically, it combines a horizontal deviation term with a depth-related term. The horizontal component discourages excessive lateral spread, while the vertical component shapes the front-to-interior balance.

The result is a plan that tends to cluster more tightly and remain more organized around the central axis. This improves coherence when the hard constraints leave substantial freedom, because compactness reduces the likelihood of unnecessarily scattered configurations.

###### Private Sanitary Zone Depth Preference

The sanitary-zone preference rewards deeper placement for bathrooms and related private service spaces. Because larger $y$ values correspond to greater interior depth in the adopted coordinate system, the penalty decreases when such spaces are moved away from the frontage.

The effect is moderate but meaningful. It does not forbid a frontward sanitary placement when necessary, but it does encourage more private positioning whenever the remainder of the plan allows it. This is a clear example of a soft rule that expresses semantic quality without threatening feasibility.

###### Residual Void Minimization

The residual void penalty measures the empty area inside the bounding box that encloses all rooms. If the rooms occupy a compact envelope, the bounding box closely approximates the total room area; if they are widely dispersed, the residual void increases. The objective therefore penalizes inefficient internal emptiness.

Formally, if $A_{bbox}$ is the area of the enclosing rectangle and $\sum_i A_i$ is the total room area, the residual void may be written as

$$
D = A_{bbox} - \sum_i A_i
$$

The solver minimizes a weighted version of $D$. This encourages compactness in both visual and structural terms, since rooms are asked to occupy their shared envelope efficiently rather than leave large unused pockets between them.

###### Seed-Conditioned Positional Guidance

Seed-conditioned guidance transfers prior design information into the solver. When a seed arrangement is available, the solver may receive suggested positions and dimensions for matching rooms. These values are not hard commitments, but they strongly bias the search trajectory.

The guidance becomes especially useful during refinement, where the intention is to preserve useful structure while still allowing limited movement. A small wiggle band may be introduced around the seed values so that the solver can adjust the layout without abandoning its overall geometry. In that sense, the guidance mechanism supports both stability and responsiveness.

###### Facade Depth Conservation

Facade depth conservation preserves the prominence of rooms that were previously aligned with the outer facade. It measures how far those rooms recede from the original frontage line and penalizes excessive inward movement.

This term is particularly useful when the plan already exhibits a clear frontage rhythm that should not be lost during refinement. It helps maintain the visible ordering of front-facing and boundary-facing rooms, thereby improving continuity across successive optimization passes.

###### Boundary Alignment Conservation

Boundary alignment conservation preserves edge harmony among rooms that were aligned in the seed layout. When two rooms were already close in boundary position and the seed overlap suggests a meaningful visual relationship, the solver is penalized if those edges drift apart.

This creates a nuanced continuity control. The system is not simply rewarding exact replication; it is protecting local alignment patterns that contribute to architectural legibility. The effect is especially relevant for facade composition, where small edge shifts can noticeably alter the appearance of the plan.

###### Recess Modulation of the Frontage Plane

Recess modulation is a more expressive form of frontage quality control. It distinguishes between shallow and severe recesses and applies different weight levels accordingly. It also introduces an attachment-oriented component that discourages nearby frontage elements from losing their relative alignment.

This produces a more refined notion of facade quality than a simple depth cap would provide. The model does not merely ask whether a room is recessed; it asks how far, how severely, and in what local context. Such richer scoring helps preserve architectural rhythm while still permitting modest variation.

###### Boundary-Coupling Reinforcement

Boundary-coupling reinforcement transforms the shared-wall expectation from a hard admissibility condition into a softer improvement target. During refinement, rooms are penalized when they fail to meet the tighter shared-boundary minimum associated with their type. The logic is consistent with the hard version, but the consequence is different: instead of rejection, the solver receives a graded cost signal.

This is a strong example of stage-sensitive design. During generation, shared boundaries help define a valid layout. During refinement, the same spatial idea becomes a quality metric that can be improved without forcing infeasibility. The result is more nuanced optimization and better control over the final plan.

#### End of This Chapter

The floor plan generator is the most structurally demanding part of the project because it must reconcile geometry, function, and design intent within a single optimization framework. Its strength lies not in any one individual rule, but in the coordinated interaction among hard feasibility constraints, staged refinement, and soft architectural preferences. The generation profile establishes a valid spatial foundation, the refinement profile polishes that foundation with limited local movement, and the constraint architecture ensures that the resulting layout remains both practical and expressive.

Viewed as a whole, the chapter demonstrates that successful floor planning is not simply a matter of drawing rectangles. It is a disciplined process of encoding architectural meaning into mathematical form and then allowing the solver to search for the most coherent arrangement that satisfies that meaning. The project’s generator achieves this by combining strict geometric legality with configurable spatial intelligence, making it the conceptual center of the entire system.

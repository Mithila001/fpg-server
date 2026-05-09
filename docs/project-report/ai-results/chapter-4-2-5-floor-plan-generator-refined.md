### Chapter 4.2.5 Floor Plan Generator

The floor plan generator constitutes the computational core of the project. It is the stage in which architectural intent is translated into a spatially feasible arrangement of rectangular rooms under a dense set of geometric, relational, and stylistic requirements. Among all components of the system, this stage consumes the greatest amount of computational effort because it must simultaneously satisfy hard feasibility conditions, preserve design intent, and retain enough freedom to produce diverse layouts.

At a conceptual level, the generator is built upon a constraint programming model solved through a CP-SAT engine. This choice is appropriate because floor planning is not merely a matter of optimization in the usual continuous sense; it is a combinatorial placement problem governed by exact relational rules. Rooms must not overlap, required adjacencies must be honored, frontage rules must be preserved, and the resulting arrangement must still remain adaptable enough to accommodate multiple viable architectural interpretations. The solver therefore operates as a balance between strict admissibility and guided exploration.

The coordinate system is significant for the interpretation of every rule. The origin lies at the bottom-left of the floor plate, the horizontal axis extends from left to right, and the vertical axis expresses depth from the frontage toward the interior. In this orientation, $y=0$ corresponds to the front edge of the plan. This convention is essential because several constraints reason directly about entrance depth, frontage preservation, and the placement of rooms that should remain near the exterior boundary. As a result, geometric optimization is not abstractly symmetric; it is semantically directional.

The generation pipeline is organized into profiles. The primary generation profile focuses on producing a fresh, feasible layout from a requirement set. The refinement profile, by contrast, accepts an existing layout and attempts to improve it through a bounded re-solve that preserves the overall composition while adjusting local spatial relationships. This staged structure is one of the most important architectural decisions in the system, because it prevents the solver from treating all layouts as if they were equally free to change. Instead, each pass carries a distinct objective: first feasibility, then controlled improvement.

The configuration panel acts as a constraint selection matrix. It allows the system to enable or disable individual families of rules without altering the underlying solver architecture. This makes the generator both experimentally flexible and analytically transparent. Different profiles are therefore not separate solvers in the strict sense, but rather different configurations of the same spatial reasoning engine.

#### Floor Plan Generation Core (Engine)

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

#### Floor Plan Generation Initialization Profile

The initialization profile is designed to build a fresh floor plan from requirement data. Its conceptual purpose is not to polish an existing arrangement, but to establish a valid structural baseline. In practical terms, this profile emphasizes hard feasibility and only a minimal set of soft biases. This makes it the most conservative profile in the system and the one most closely aligned with first-pass generation.

A notable feature of this profile is the use of point-based hints to derive an initial spatial tendency. These hints are not equivalent to hard geometric commitments. Rather, they provide the solver with a plausible starting direction derived from the input requirements. This helps the system begin the search within a relevant region of the solution space, while still allowing the engine to explore alternatives when necessary. In this sense, the hints serve as initialization guidance rather than as rigid design locks.

The initialization profile is intentionally focused on enforcing hard conditions that are necessary for validity. The generated layout must respect non-overlap, room shape limits, adjacency logic, and frontage semantics before any stylistic concerns are considered. This reflects a common architectural principle: a plan must first be admissible before it can be aesthetically refined.

Because the generation profile is meant to establish the first workable layout, it typically avoids heavy dependence on seed-based penalties. That separation is important. If the first pass were overly constrained by prior arrangement logic, it could fail to discover a legitimate baseline in the first place. The profile therefore prioritizes feasibility, structural coherence, and broad search freedom within the legal design envelope.

#### Floor Plan Generation Refinement Profile

The refinement profile represents the second major phase of the generator. Whereas the initialization profile seeks a valid arrangement from scratch, the refinement profile assumes that a layout already exists and attempts to improve it without destroying its overall structure. This is a classic local-search strategy: the system reuses an existing solution as context and asks the solver to produce a better nearby variant.

The distinctive feature of refinement is bounded movement. Rather than permitting unrestricted repositioning, the solver is given a limited spatial wiggle around the prior solution. This ensures that the resulting output remains recognizably related to the original plan. Such bounded adjustment is especially useful when the goal is iterative design development, where each pass should polish the composition rather than replace it wholesale.

The refinement profile also introduces a richer set of soft preferences. These preferences do not block feasibility, but they do reshape the ranking of candidate layouts. As a result, the solver is encouraged to preserve useful alignments, reduce wasted area, maintain facade clarity, and improve the quality of shared walls. The profile is therefore less about simply satisfying constraints and more about increasing the architectural maturity of an already viable plan.

Conceptually, the refinement process can be applied more than once. Each pass may receive the output of the previous pass, creating a multi-stage improvement sequence. This is valuable because certain spatial qualities emerge only gradually. A first refinement may recover structure; a second may improve compactness; a third may sharpen facade order. The architecture of the solver supports this layered improvement model without requiring a distinct algorithm for each pass.

The refinement profile also reveals an important philosophy of the system: not all constraints should be treated equally in every phase. Early in the process, feasibility dominates. Later, a richer set of descriptive preferences can be brought into play. This staged approach reduces the risk of overconstraining the solver too soon and improves the interpretability of the final output.

#### Floor Plan Generation Constraints

The constraint system is the principal mechanism through which architectural intent is encoded into the solver. It is divided into hard and soft families. Hard constraints define feasibility; soft constraints define preference. The distinction is fundamental. If a hard rule fails, the arrangement is invalid. If a soft rule is violated, the arrangement may still be acceptable, but it receives a worse score.

The following discussion excludes auxiliary extender behavior, since that pathway belongs to a separate architectural branch and is not part of the main generation and refinement narrative in this chapter.

##### Overview of Constraint Contribution

Together, the constraints perform three tasks. First, they prevent physically impossible layouts such as overlapping rooms or invalid room proportions. Second, they enforce functional relationships such as adjacency, frontage, and circulation. Third, they encode qualitative expectations such as compactness, facade continuity, and semantic depth. The generator is therefore not merely placing rectangles; it is evaluating whether the spatial arrangement expresses a coherent house-like composition.

Hard rules dominate the feasibility envelope, while soft rules adjust the solver’s preference landscape. This balance is what makes the system practical. Without hard rules, the output would be structurally unreliable. Without soft rules, the output would be valid but often blunt or underdesigned. The combination allows the plan to remain both legal and expressive.

##### Basic Geometry Constraints

Basic geometry constraints establish the lowest level of structural validity. They prevent room overlap and ensure that every room’s boundary coordinates remain internally consistent with its position and dimensions. In addition, each room is subject to aspect-ratio limits so that extremely thin or flattened shapes do not emerge in ordinary cases.

This constraint family is especially important because it forms the geometric foundation for every other rule. If two rooms are allowed to overlap, or if a room can violate its own boundary logic, then adjacency and frontage reasoning become meaningless. The model must first know where each room begins and ends before it can reason about shared walls or circulation paths.

The aspect-ratio logic is also noteworthy. Most room types are held within general width-to-height bounds, while some types receive special treatment because their functional geometry differs from the norm. For example, spaces such as garages and verandas typically tolerate more elongated proportions than a standard interior room. This distinction is not cosmetic; it prevents the solver from producing mathematically valid but practically implausible shapes.

##### Hallway Constraints

Hallway constraints ensure that circulation spaces behave like genuine passage elements rather than arbitrary rectangular fill zones. A hallway is required to have a narrow dimension within a controlled range and a sufficiently long opposing dimension. This preserves the recognizability of the hallway as a linear connector.

Beyond shape, hallway logic also addresses connectivity. Hallways are expected to touch the living area and at least one additional non-living room, either directly or through a controlled chain of hallway adjacency. This prevents circulation from becoming isolated or functionally meaningless. The solver therefore treats hallways as connective tissue in the spatial organization of the house.

The rule set also counts shared walls. A hallway is expected to have a minimum number of fully shared sides with neighboring rooms, which encourages corridor integration rather than isolated placement. This is an important spatial quality because a hallway that floats without adequate wall contact tends to look and function like an accidental void rather than a deliberate circulation route.

##### Room Shared Wall Constraints

Shared wall constraints encode enclosure and adjacency quality on a per-room-type basis. Instead of treating every room as equally open, the system allows each type to carry its own expectations about how many of its sides should be fully shared with neighboring rooms. This is especially useful for distinguishing between public, private, and transitional spaces.

The hard version of this rule counts the number of sides that are fully shared and verifies that the selected sides satisfy the type-specific minimum and maximum thresholds. A small relaxation margin may be permitted through a wiggle percentage, allowing the solver to accept near-complete alignments when the coverage is close enough. This makes the rule robust without becoming brittle.

This family of constraints is important because it governs more than adjacency in the narrow sense. It influences whether a room feels embedded in the plan or exposed at the edges. Rooms with stronger shared-wall requirements tend to sit deeper within the arrangement, while rooms with looser rules may appear more peripheral. The result is a subtle but powerful form of spatial hierarchy.

##### Hard Room Adjacency Constraints

Hard adjacency constraints are driven by relation data that expresses mandatory functional connections between room types. The solver distinguishes between two hard styles of relation. In one style, a room must satisfy adjacency against one or more specified target types. In the other, adjacency is required across a broader set of alternatives, allowing the solver to choose among multiple compatible targets while still preserving the underlying necessity.

The adjacency relation is not merely a yes-or-no touch rule. It also includes a minimum overlap threshold, which prevents accidental point contact from being mistaken for meaningful adjacency. This is essential because functional room relationships usually require a real shared boundary, not a negligible geometric coincidence.

This rule family shapes the functional graph of the house. It determines which rooms can plausibly communicate with one another and which separations are too severe to remain acceptable. As a consequence, adjacency constraints often exert more influence over the lived logic of the plan than over its visual appearance.

##### Minimum Area Coverage

The minimum area coverage rule ensures that the combined room areas occupy at least a configured proportion of the total floor plate. In other words, the design must not leave the plan excessively underused. This guards against layouts that are technically feasible but spatially sparse.

Formally, if $A_{floor}$ is the full floor area and $A_i$ are the room areas, the rule requires

$$
\sum_i A_i \geq \rho A_{floor}
$$

where $\rho$ is the minimum coverage ratio. This creates a global coupling across all rooms, because the feasibility of the entire arrangement depends on the aggregate occupied area rather than on any one room in isolation.

Although this constraint is present in the architecture, it is not always enabled in the default profile. That is a sensible choice. In tight designs, a strict minimum-coverage rule can conflict with frontage, adjacency, and shape restrictions. Keeping it available but optional makes the system more adaptable across different design scenarios.

##### Room Size Hierarchy

Room size hierarchy constrains each configured room type to occupy a percentage band of the living area. The living area serves as the reference anchor, and other room types are scaled relative to it. This expresses a semantic hierarchy in which the living room is not only spatially important but also structurally informative.

This rule protects the plan from disproportionate room sizing. A bedroom, kitchen, bathroom, veranda, or garage can each be given a target range that reflects architectural expectation rather than pure geometric possibility. As a result, the solver is discouraged from producing rooms that are technically valid but socially implausible.

The rule is currently a configurable hard option rather than a universally active one. This reflects the fact that proportional room sizing can be very useful in some layouts but overly restrictive in others. The architecture therefore keeps it available as a controlled design policy rather than a universal mandate.

##### Anchor Room Location Constraint

Anchor room location logic introduces a macro-level directional order to the plan. The frontage side is the front of the house, and spaces that are meant to mediate that frontage must remain nearer to the exterior edge than deeper interior rooms. If a veranda exists, it becomes the primary anchor; otherwise, the living area serves that function.

This rule is conceptually important because it prevents the solver from generating a plan with the frontage logic inverted or spatially ambiguous. The plan should not simply be a set of adjacent rooms; it should express a depth hierarchy from public entry toward private interior. The anchor rule enforces that hierarchy with a geometric comparison of room centers.

The effect is subtle but powerful. By stabilizing the front-to-back ordering, the rule reduces symmetry-related drift and makes the overall arrangement more legible. It is therefore a structural semantic constraint rather than a local geometric one.

##### Veranda Placement Constraints

Veranda placement is one of the most distinctive hard rules in the system. The veranda is fixed to the front boundary so that it clearly mediates the relationship between the house and the exterior. In addition, the system creates an auxiliary outdoor-space region associated with the veranda, which helps preserve the intended frontage composition.

The veranda must attach along one side to this outdoor space, and the outdoor space itself is arranged so that it does not overlap with other real rooms. This means the frontage is not treated as an abstract line; it is treated as a structural interface with its own reserved geometry. The veranda therefore becomes more than a simple room type. It becomes a frontage organizer.

This rule family is especially valuable because it protects a highly recognizable architectural feature from being absorbed into the general room pool. It ensures that the front edge of the plan retains a clear civic and spatial identity.

##### Garage Placement Constraints

Garage placement constraints enforce side anchoring and access logic. The garage must lie near exactly one lateral boundary, either left or right, which gives the plan a clear vehicular orientation. This avoids ambiguous central garage placement that would weaken the exterior organization.

Access is equally important. The garage must either sit directly on the front boundary or receive access through an aligned outdoor-frontage segment. This means the garage is not only spatially attached to the boundary, but also functionally reachable in a way that resembles real use. The rule therefore combines geometric placement with practical circulation semantics.

This constraint family has a strong effect on feasibility because garages occupy a specialized role in frontage composition. If the frontage is already crowded by other hard rules, the garage may become difficult to place. That is not a flaw; it is evidence that the solver is negotiating a realistic design tradeoff.

##### Envelope Staircase Constraints

The envelope staircase rule shapes the outer massing of the plan by enforcing setback behavior along selected exterior sides. Instead of allowing every room to flush directly against the envelope, the solver is encouraged to produce stepped edges with controlled gaps. This gives the overall massing a more articulated profile.

The rule is based on the idea that a room exposed to the exterior should maintain a positive clearance relationship with neighboring rooms along designated sides. The result is not a strict perimeter polygon in the conventional sense, but a sequence of controlled offsets that create architectural variation in the outline.

This constraint can significantly influence the plan’s character because it affects not just room placement but also the visual rhythm of the massing. It is therefore a rule about form as much as function.

##### Kitchen-Hallway Back-Wall Setback Constraint

This rule requires at least one eligible kitchen or hallway back wall to preserve a clear setback behind it. The purpose is to avoid placing a functional back wall too tightly against the interior boundary, where door clearance and circulation depth may become inadequate.

The constraint examines the vertical distance from the room’s back wall to the floor boundary and checks whether the adjacent zone remains free from intrusive room geometry. This creates a protected depth band that improves functional usability. It is a targeted rule rather than a global one, which makes it more precise than a general setback constraint.

Its significance lies in its focus on practical circulation quality. Certain room types need to maintain a comfortable back-wall buffer, and this rule protects that requirement without imposing a blanket restriction on the entire plan.

##### Hard Dining-Room Relation Constraint

The dining room has a special relational role in the plan. It must connect either directly or through a single hallway step to both the living area and the kitchen. This preserves the expected social and functional adjacency between shared eating space, food preparation space, and the principal gathering area.

The constraint allows a modest degree of indirection through hallway mediation, which is important in layouts where direct touching is not possible. At the same time, it prevents the dining room from drifting into an isolated location that would weaken the coherence of the household circulation network.

This rule is especially noteworthy because it expresses architectural logic as a graph-like relation rather than merely a positional one. It helps ensure that the dining room remains part of the social core of the house.

##### Soft Room Adjacency Preference

Soft adjacency preference uses the same touch logic as the hard adjacency family, but it translates the result into a preference structure rather than a feasibility requirement. The solver can therefore benefit from the adjacency signal without being forced into a narrow set of exact placements.

This mechanism is valuable in principle because it preserves flexibility. However, its practical effect is currently limited because the generated preference variables are not fully integrated into the objective in the present wiring. Conceptually, it still matters: it defines the candidate adjacency space and prepares the model for future scoring integration.

##### Compact Layout Center Proximity

The compactness objective encourages rooms to remain near the horizontal center of the floor plate while also biasing the arrangement toward the front side. Mathematically, it combines a horizontal deviation term with a depth term. The horizontal component discourages excessive lateral spread, while the vertical component reduces the penalty as rooms are placed deeper into the front-oriented coordinate frame.

The result is a layout that tends to cluster more tightly and remain more organized around the center line. This can improve plan cohesion, especially when the hard constraints leave substantial freedom. In such cases, compactness helps prevent the arrangement from drifting into unnecessarily scattered configurations.

##### Bathroom Location Preference

Bathroom location preference is a soft rule that rewards deeper placement. Because the coordinate system treats larger $y$ values as more interior, the penalty decreases when the bathroom is moved away from the front boundary. This aligns with common privacy expectations in residential planning.

The penalty is modest but meaningful. It does not prevent bathrooms from appearing near the front when necessary, but it does nudge the solver toward more private positioning whenever the rest of the layout allows it. This is a good example of a soft rule that expresses semantic quality without endangering feasibility.

##### Layout Dead-Space Penalty

The dead-space penalty measures the empty area inside the bounding box that encloses all rooms. If the rooms occupy a compact envelope, the bounding box closely approximates the total room area; if they are spread apart, the dead space increases. The objective therefore punishes wasted internal void.

Formally, if $A_{bbox}$ is the area of the enclosing rectangle and $\sum_i A_i$ is the total room area, then dead space can be expressed as

$$
D = A_{bbox} - \sum_i A_i
$$

The solver minimizes a weighted version of $D$. This encourages compactness not only in a visual sense, but in a structural one: rooms should occupy the shared envelope efficiently rather than leaving large empty pockets between them.

##### Seed Layout Hints

Seed layout hints are a guidance mechanism that transfers prior design information into the solver. When a seed is available, the solver may receive suggested positions and dimensions for matching rooms. These are not hard constraints, but they strongly bias the search trajectory.

The hints become especially useful during refinement, where the purpose is to preserve useful structure while still allowing limited movement. A small wiggle band may be added around the seed values so that the solver can adjust the layout without abandoning its overall geometry. This makes the refinement process both stable and responsive.

##### Seed Facade Depth Penalty

The seed facade depth penalty preserves the prominence of rooms that were previously aligned with the outer facade. It measures how far those rooms recess from the original facade lines and penalizes excessive inward movement. In this way, the solver is encouraged to respect the earlier frontage composition instead of eroding it.

This penalty is particularly useful when the plan already has a clear facade rhythm that should not be lost during refinement. It helps maintain the visible ordering of front-facing and boundary-facing rooms, thereby improving the continuity of the design across successive passes.

##### Seed Facade Alignment Penalty

The alignment penalty preserves edge harmony between rooms that were aligned in the seed layout. When two rooms were already close in their boundary positions and their seed overlap suggests a meaningful visual relationship, the solver is penalized for allowing those edges to drift apart.

This creates a nuanced form of continuity control. The system is not simply rewarding exact copying; it is protecting local alignment patterns that contribute to architectural legibility. The effect is especially important for facade composition, where small edge shifts can noticeably alter the appearance of the plan.

##### Recessed Facade Penalty

The recessed facade penalty is a more expressive version of frontage quality control. It distinguishes between shallow and severe recesses and applies different weight levels accordingly. It also adds an attachment-oriented component that discourages nearby facade elements from losing their relative alignment.

This produces a more refined notion of facade quality than a simple depth cap would. The model does not merely ask whether a room is recessed; it asks how far, how severely, and in what local context. This richer scoring structure helps the solver preserve architectural rhythm while still permitting modest variation.

##### Room Shared Wall Refinement Penalty

The shared-wall refinement penalty transforms the shared-wall expectation from a hard admissibility rule into a softer improvement target. In the refinement stage, rooms are penalized when they fail to meet the tighter shared-wall minimum for their type. The logic is consistent with the hard rule, but the consequence is different: instead of rejection, the solver receives a graded cost signal.

This is an excellent example of stage-sensitive design. During generation, shared walls help define a valid layout. During refinement, the same spatial idea becomes a quality metric that can be improved without forcing infeasibility. The result is more nuanced optimization and better control over the final plan.

#### End of This Chapter

The floor plan generator is the most structurally demanding part of the project because it must reconcile geometry, function, and design intent within a single optimization framework. Its strength lies not in any one individual rule, but in the coordinated interaction among hard feasibility constraints, staged refinement, and soft architectural preferences. The generation profile establishes a valid spatial foundation, the refinement profile polishes that foundation with limited local movement, and the constraint architecture ensures that the resulting layout remains both practical and expressive.

Viewed as a whole, the chapter demonstrates that successful floor planning is not simply a matter of drawing rectangles. It is a disciplined process of encoding architectural meaning into mathematical form and then allowing the solver to search for the most coherent arrangement that satisfies that meaning. The project’s generator achieves this by combining strict geometric legality with configurable spatial intelligence, making it the conceptual center of the entire system.

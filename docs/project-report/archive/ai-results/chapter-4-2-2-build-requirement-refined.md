### Chapter 4.2.2 Build Requirement

The build requirement stage functions as the formal pre-processing layer for the floor plan generation pipeline. Its role is not to synthesize geometry directly, but to transform a loosely specified user request into a validated and solver-ready requirement package. In this sense, the stage serves as a semantic and numerical normalization boundary: it ensures that the subsequent optimization process receives a coherent set of room definitions, floor dimensions, and relational constraints. By performing this work before the solver is invoked, the system reduces the probability of infeasible trials, minimizes unnecessary search space, and enforces a consistent interpretation of the design brief.

At a high level, this stage performs three complementary tasks. First, it validates the supplied room template and rejects incomplete or structurally inconsistent inputs. Second, it retrieves the relevant constraint knowledge stored on the server, including room-size limits and inter-room relationship rules. Third, it mutates and harmonizes the request so that all values are compatible with the generation process. The result is a single consolidated requirements object that becomes the shared reference for later optimization, scoring, and post-processing phases.

#### Validation

Validation begins by checking whether the room template contains the mandatory room categories required for meaningful floor plan generation. A small illustrative example includes a sleeping room, a kitchen, a bathroom, and a veranda or similar access-related space. These are mandatory not because they are conceptually universal, but because the downstream solver expects a minimum semantic structure from which it can derive adjacency, circulation, and envelope relationships. In practice, a floor plan without these foundational room types would provide insufficient information for the constraint system to construct a viable household composition.

The validation step also prevents the solver from operating on ambiguous or incomplete room templates. Since the optimization process is driven by constraints, missing structural elements can lead to a chain of infeasible relationships later in the pipeline. A solver that is asked to satisfy adjacency, area, and accessibility conditions must know which spaces are present from the outset. Therefore, the validation layer acts as a safeguard against both logical inconsistency and computational waste.

In effect, this step establishes the minimum semantic completeness required for the generation process. It does not merely check that the input is syntactically well-formed; it verifies that the template contains the room categories necessary to support a valid constraint network.

#### Dimension Calculation and Aspect Ratio

A second function of the build requirement stage is to estimate a suitable floor envelope from the room composition itself. This is important because the search space of a floor plan generator grows rapidly as available area increases. If the outer boundary is left excessively large, the solver must explore a much wider combination of placements, which can reduce efficiency and increase the likelihood of weak or misleading solutions. To avoid this, the system reduces the effective floor space according to the minimum spatial requirements implied by the room set.

Let the minimum width and height of room $i$ be $w_i^{\min}$ and $h_i^{\min}$, and let the corresponding maximum values be $w_i^{\max}$ and $h_i^{\max}$. A conservative lower bound on the total area required by the template can be expressed as

$$
A_{\min} = \sum_{i=1}^{n} w_i^{\min} h_i^{\min} + A_{\text{buffer}}.
$$

Likewise, an upper bound is given by

$$
A_{\max} = \sum_{i=1}^{n} w_i^{\max} h_i^{\max} + A_{\text{buffer}}.
$$

The buffer term $A_{\text{buffer}}$ represents a small additional allowance used to absorb geometric friction such as circulation loss, alignment overhead, or auxiliary spacing. This prevents the envelope from being reduced too aggressively and allows the solver to retain a realistic amount of flexibility.

The aspect ratio is handled through a feasibility test against the buildable envelope. If the requested ratio is represented by

$$
r = \frac{H}{W},
$$

then the system seeks a rectangle that respects both the requested ratio and the available buildable limits. Given maximum floor width $W_{\max}$ and maximum floor height $H_{\max}$, the largest feasible width under the ratio is constrained by three conditions:

$$
W \le W_{\max}, \qquad W \le \frac{H_{\max}}{r}, \qquad W \le \sqrt{\frac{A_{\max}}{r}}.
$$

The selected width is therefore

$$
W^* = \min\left(W_{\max},\, \frac{H_{\max}}{r},\, \sqrt{\frac{A_{\max}}{r}}\right),
$$

and the corresponding height is

$$
H^* = rW^*.
$$

This adjustment logic is intentionally conservative. Rather than blindly accepting the requested aspect ratio, the system verifies whether that ratio can coexist with the available geometry and the total spatial demand of the room set. If the resulting rectangle still fails to meet the minimum required area, the request is considered geometrically incompatible and is rejected early.

#### Load Server Constraints

Once the request has been validated geometrically, the system loads server-side constraints that define the allowable behavior of each room type. Room-size constraints specify the admissible width, height, and area ranges for a room category under a particular size label. For example, a compact bedroom might be permitted to occupy a relatively small footprint, whereas a larger kitchen may require a wider interval. These records allow the solver to distinguish between room categories without hard-coding geometry into the request itself.

A relation constraint describes how one room type should interact with others. It typically includes the subject room type, a list of related room types, and an enforcement level that indicates whether the relationship is mandatory or preferential. For instance, a bedroom may be associated with a bathroom under a strong adjacency rule, while a kitchen may be allowed to connect to either a dining room or a living room under a softer alternative rule. Conceptually, the enforcement level determines how strictly the solver must preserve the relation, and the related-room list defines the admissible partners in that relation.

These loaded constraints become part of the solver’s formal objective and feasibility structure. In a CP-SAT setting, they serve as explicit declarative conditions rather than procedural instructions. The value of this design is that the same solver can support multiple layout archetypes by simply changing the constraint dataset, without modifying the optimization logic itself.

#### Majority Size Selection

The build requirement stage also performs a normalization pass over room size labels. If a template contains several size labels, the system identifies the most frequently occurring one and promotes it as the dominant category. All rooms are then converted to that category, except where a special case is explicitly preserved. This is a pragmatic safety mechanism designed to protect the solver from highly heterogeneous size distributions that may exceed the assumptions of the current generation pipeline.

The underlying idea is simple: if most rooms in a template are intended to operate at a common scale, then treating the entire template under that dominant scale produces a more stable and predictable constraint set. This reduces the risk that a minority of unusually large or small rooms will distort the feasible region for the rest of the plan. In other words, the majority label acts as a statistical regularizer for the room set.

#### Prune Relations

After room-size normalization, the system prunes relation constraints so that only relationships relevant to the actual template remain. This step is critical because relation data may contain room types that are present in the broader database but absent from the current request. If such a rule were left intact, the solver could be asked to satisfy a relationship involving a room that does not exist in the active template, producing an impossible or meaningless condition.

For example, imagine a relation rule that expects a veranda to connect to a front-facing circulation space, but the current template contains no veranda at all. Keeping that rule would force the solver to reason about a non-existent room, which introduces an artificial contradiction. By removing relations whose room types are not present, the system ensures that every remaining rule is anchored in the actual problem instance. This pruning step is therefore not merely an optimization; it is a necessary alignment between the knowledge base and the request-specific template.

#### Assemble Final Package

After validation, geometric adjustment, constraint loading, size normalization, and relation pruning have been completed, the stage assembles a single final requirements package. This package contains the normalized room list, the validated configuration values, and the filtered relation constraints. In operational terms, it becomes the canonical data structure passed into the later phases of the floor plan pipeline.

The significance of this final package is architectural as well as computational. Rather than allowing each downstream module to re-interpret raw user input independently, the system centralizes all pre-processing decisions into one normalized object. This improves consistency, reduces duplicate validation logic, and creates a clear separation between requirement preparation and actual generation.

### Overall Assessment

Overall, the build requirement stage is the methodological foundation of the floor plan generation system. It transforms an informal design brief into a rigorously structured optimization input, ensuring that the solver operates within a meaningful and feasible search domain. Its contribution is especially important because it mediates between human-authored intent and machine-enforced constraints. The result is a more stable generation process, a lower rate of infeasible trials, and a more reliable interpretation of spatial requirements.

From a systems perspective, this stage behaves like a gatekeeper and a translator at the same time. It rejects invalid inputs, reconciles conflicting assumptions, and encodes the request into a standardized solver-ready format. In doing so, it establishes the conditions under which the rest of the floor plan pipeline can produce high-quality results with greater computational efficiency.

Reviewer Notes: I replaced implementation-level references with conceptual descriptions, clarified the mandatory-room discussion to avoid overstating universal requirements, and expressed the dimension logic with general mathematical forms consistent with the observed preprocessing behavior.

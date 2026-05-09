# Chapter 4.2.2 — Build Requirement (Refined)

This section formalizes the transformation of user-provided spatial and programmatic requirements into a compact, solver-ready payload that the generative planning pipeline consumes. The process operates as a pre-processing and verification layer whose objectives are (1) to validate intent and completeness, (2) to translate qualitative preferences into quantitative bounds, (3) to reduce the search space through conservative spatial budgeting, and (4) to produce a single cohesive requirements object for downstream optimization.

**Primary Responsibilities**

- Validate user-provided programmatic requirements and detect missing mandatory elements.
- Query and integrate authoritative constraint data from the server-side repository of room size categories and relational rules.
- Compute a reduced, feasible spatial envelope (dimensioning and aspect ratio) that contains the required program while limiting solver search volume.
- Normalize room-size categories to a dominant scale when needed to avoid pathological combinations.
- Prune or degrade relational constraints that cannot be satisfied given the template, preventing solver infeasibility.
- Produce a single, self-contained requirements package for the planner.

**Validation of Programmatic Completeness**

The first stage checks whether the submitted program contains a minimal set of room types that the optimization model requires to anchor a feasible solution. Typical mandatory room types (illustrative, chosen for algorithmic stability) include a primary habitable space (e.g., a living or main lounge), a food-preparation space (kitchen), at least one sanitation facility (bathroom), and a primary sleeping space (bedroom). These core types are mandatory because the constraint-satisfaction formulation relies on them to establish essential adjacency, circulation and service relationships; omitting them can create under-constrained variables that destabilize search heuristics.

When a mandatory type is absent the pre-processor performs one of the following, depending on user intent and system policy:

- Flag the requirement as invalid and request clarification; or
- Insert a minimal placeholder with conservative minimum dimensions and low-priority metadata, enabling the solver to proceed while highlighting the intervention to the user.

Each validation outcome is recorded in the final package as a validation status and a short remediation suggestion.

**Dimension Calculation and Aspect-Ratio Feasibility**

To avoid presenting the solver with an overly permissive design domain, the build-requirement stage computes a conservative spatial budget that tightly bounds the solution space while preserving feasibility. The computation proceeds from per-room minimum area expectations and a configurable buffer fraction for circulation and services.

Let the set of rooms in the validated template be $R$. For each room $i\in R$ denote a conservative minimum area estimate by $a_i^{\min}$. The system computes the minimum total program area:

$$A_{\text{min}} = \sum_{i\in R} a_i^{\min}$$

and a guarded program area that includes a buffer fraction $\beta$ (e.g., $\beta = 0.10$ for a 10% allowance for circulation):

$$A_{\text{program}} = (1 + \beta)\,A_{\text{min}}$$

If the user supplies a desired aspect ratio $r_{\text{user}} = W/H$, this is tested for geometric feasibility against the buildable bounds in the site context. Using the area $A_{\text{program}}$ and a candidate aspect ratio $r$, the implied envelope dimensions are

$$W(r) = \sqrt{A_{\text{program}}\,r}, \quad H(r) = \sqrt{\tfrac{A_{\text{program}}}{r}}.$$

Feasibility constraints take the form

$$W_{\min} \le W(r) \le W_{\max}, \qquad H_{\min} \le H(r) \le H_{\max},$$

where the box bounds $(W_{\min},W_{\max},H_{\min},H_{\max})$ derive from site/building limits or administrative maxima. Solving the width inequalities for $r$ yields a feasible interval

$$r_{\min} = \frac{W_{\min}^2}{A_{\text{program}}}, \qquad r_{\max} = \frac{W_{\max}^2}{A_{\text{program}}},$$

and an analogous pair from height limits; the intersection of these intervals forms the admissible aspect-ratio range. If $r_{\text{user}}$ lies outside that intersection, the build requirement logic projects it to the nearest bound (i.e., $r^* = \operatorname{clamp}(r_{\text{user}}, r_{\min}, r_{\max})$) and records a rationale for the adjustment. This projection preserves the user's preference as closely as possible while guaranteeing a feasible envelope for the solver.

The envelope area and adjusted aspect ratio are included in the package as the spatial budget and provide the solver with fixed outer bounds that substantially reduce combinatorial complexity.

**Loading Server-Side Constraints**

This stage retrieves two canonical datasets from the authoritative constraint repository: (1) room-size category definitions and (2) inter-room relational rules. Room-size category entries encode conservative geometric limits by category label (for example: `compact`, `regular`, `generous`), each specifying minimum and maximum width, height, and area intervals. A small example (conceptual): a `regular` bedroom might list $w\in[3.0,4.2]\,\mathrm{m}$, $h\in[2.8,4.0]\,\mathrm{m}$ and an area range $a\in[8.4,16.8]\,\mathrm{m}^2$.

Relational rules describe desired or required spatial relationships between two room types. Example relation types include `adjacency` (rooms must share a boundary), `proximity` (rooms should be within a distance band), `service` (one room must be accessible from another via a service sequence), and `orientation_preference` (e.g., living areas prefer a certain solar exposure). Each relation object contains keys such as:

- `constraint_priority`: a scalar indicating strictness (e.g., required vs preferred),
- `subject_room` and `object_room`: the two room types involved,
- `relation_type`: adjacency/proximity/containment/etc.,
- `distance_range` or `shared_edge_min`: quantitative bounds where applicable, and
- `context_filters`: applicability conditions (e.g., only when both rooms appear and are not marked as auxiliary).

These objects are interpreted into constraints within the solver; higher `constraint_priority` yields either a hard constraint or a strongly-weighted objective penalty.

**Majority Size Selection**

To curb combinatorial explosion arising from heterogeneous mixing of many size classes, the system inspects the room template and computes a modal size category (the label with the highest incidence across rooms). When the modal share exceeds a configurable threshold, the pre-processor normalizes the majority of room entries to this modal category. The rationale is pragmatic: many projects assume a consistent scale (for example, a predominantly `regular` apartment) and forcing a dominant scale reduces unnecessary variability that would otherwise multiply search branches.

This is implemented conservatively: rooms that semantically require an alternate category (e.g., a service room that must be `compact`) are exempted, and a record of any forced conversions is added to the package so downstream reviewers can audit the normalization.

**Pruning and Degradation of Relations**

Relational rules may reference room types that do not appear in the validated program. A naïve attempt to apply such a relation creates unsatisfiable constraints. Therefore, the pre-processor prunes relations whose subject or object rooms are absent. For relations that are desirable but not essential, the system may degrade the relation by lowering the `constraint_priority` and translating the rule into a soft objective instead of a hard constraint.

Example: suppose a `pantry--kitchen` adjacency rule exists but the template contains no `pantry`. The pre-processor will remove the rule; if the user has flagged pantry as an optional wish, the system may instead append a high-level suggestion to the metadata rather than enforce an impossible adjacency.

**Assemble Final Package**

At completion the build-requirement stage emits a single structured package containing:

- `validation_status` and `remediation_notes`;
- `spatial_budget`: $(A_{\text{program}}, r^*, W^*, H^*)$;
- `room_specifications`: an array of room descriptors with size-category, conservative $a^{\min}$, and dimension intervals;
- `relational_constraints`: pruned and normalized relations with explicit priority flags;
- `solver_options`: policy choices (buffer fraction $\beta$, majority normalization threshold, strict-vs-soft translation rules);
- `metadata`: provenance, timestamps, and a changelog of any automated adjustments.

This consolidated object is intentionally self-sufficient: downstream components treat it as authoritative input and need not query the server for most routine decisions.

**Overall Assessment and Role in the Pipeline**

The build-requirement stage is a critical risk-mitigation and domain-conditioning module. By converting qualitative user intent into quantitatively bounded, solver-friendly constraints, it substantially reduces the search space, prevents easy sources of infeasibility, and encodes project-level policy choices that guide the planner toward realistic solutions. Its conservative heuristics (buffering, majority normalization, and relation pruning) are intentionally risk-averse; they prioritize feasibility and traceability over maximal stylistic fidelity, while preserving audit trails so that users can review and override automated choices.

**Reviewer Notes**

- Expanded all inline guidance into formal descriptions and rationale; replaced informal examples with academically phrased illustrations.
- Introduced conservative buffer fraction $\beta$ and provided explicit formulas for area and aspect-ratio feasibility.
- Defined canonical relation object fields and described their intended semantics (priority, relation_type, quantitative bounds).
- Assumed illustrative mandatory room types and category examples to ground the narrative; these assumptions are flagged for user review.

File saved to the report results folder for integration and review.

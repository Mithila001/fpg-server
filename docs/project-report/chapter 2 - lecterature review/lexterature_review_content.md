**_ Reference Number: 1 _**

# Literature Review Extraction: Procedural Floor Plan Generation

## 1. Context

The authors aimed to solve the problem of real-time procedural generation of natural-looking building floor plans, specifically suburban houses, primarily for use in dynamic virtual environments like video games[cite: 8, 9, 15, 25, 291]. They identified that existing automated methods often wasted space during corridor placement, making the resulting layouts unrealistic compared to actual architectural practices[cite: 11, 12, 54].

## 2. Approach

The core methodology is based on the Squarified Treemap algorithm[cite: 49, 148]. The generation pipeline consists of several distinct steps:

- **Outer Shape & Sizing:** Determining a strictly rectangular outer building shape based on statistical aspect ratios[cite: 64, 69, 87].
- **Hierarchy & Room Placement:** Using a priority list and census data probabilities to assign room functionalities (e.g., social, private, service) into a hierarchy tree[cite: 102, 105, 108, 114]. The Squarified Treemap algorithm is then used to subdivide the rectangular space into smaller rectangular rooms[cite: 148, 149].
- **Connectivity & Corridors:** A connectivity graph is created to map required room adjacencies[cite: 65, 163]. To minimize wasted space, the algorithm identifies a "corridor graph," prunes it, and applies a shortest path algorithm[cite: 204, 205, 206, 208]. It then optimizes the corridor by mathematically shifting or lengthening edges to accommodate doors[cite: 211, 213, 214, 220].
- **Detailing:** Rule-based placement of doors and windows along shared walls[cite: 67, 259, 262].

## 3. Evidence

The authors validate their approach through visual comparisons, placing their generated 2D floor plans and 3D realizations side-by-side with an actual architect-designed floor plan[cite: 283, 284]. They state the results show "utmost similarity to real floor plans" and successfully eliminate the long, unused corridors seen in previous algorithms[cite: 285, 286, 300]. The algorithm achieves this performance in "real-time," making it suitable for game engines[cite: 8, 272, 294].

## 4. Critique

- **Geometric Limitations:** The algorithm restricts the building's outer shape strictly to a rectangle and inherently relies on the Treemap algorithm, which only generates rectangular internal subdivisions[cite: 69, 149, 152].
- **Statistical vs. Regulatory:** The system dictates room sizes and inclusion based on probability distributions extracted from Canadian census data[cite: 102, 103, 112]. It is not built to handle hard architectural constraints or strict building codes.
- **Domain Constraint:** The model is heavily tailored to North American suburban homes[cite: 95]. While the authors claim the parameters can be adjusted for other buildings [cite: 62], it would require manual re-calculation of statistical distributions[cite: 117].

## 5. Comparative Analysis against Your Project

**Areas of Overlap (Validating your approach):**

- **Two-Stage / Graph-Based Logic:** Just as your project uses a 2-stage skeleton generation via graph relationships, this paper also relies on constructing a hierarchy tree and a connectivity graph before physical placement[cite: 65, 108, 252].
- **Holistic Spatial Generation:** Both your project and this paper explicitly model the entire ecosystem of a floor plan, prioritizing room placement, adjacency, optimized circulation (corridors), doors, and windows[cite: 64, 65, 66, 67].
- **Performance:** Both solutions successfully achieve rapid layout generation, with your project hitting 1-3 minutes and the paper achieving real-time rendering[cite: 8, 294].

**Key Gaps (Highlighting your selling points):**

- **CP-SAT & Optuna vs. Squarified Treemaps:** You utilize an advanced CP-SAT solver and Optuna, which allows for complex constraint satisfaction. The paper relies on a much simpler Squarified Treemap space-packing algorithm[cite: 49, 148].
- **Regulatory Compliance vs. Game Design:** The paper's explicit use case is video games, relying on probabilistic census data for room sizing[cite: 8, 100, 102]. Your project serves a real-world utility for landowners by enforcing strict Sri Lankan building regulations (setbacks, minimum sizes) as hard mathematical constraints.
- **Rectilinear Shapes vs. Rectangles Only:** The paper strictly generates rectangular rooms and rectangular outer bounds[cite: 69, 150]. Your post-processing wall extension feature represents a significant geometric upgrade by generating realistic rectilinear room shapes.
- **Modularity:** While the paper allows for manual parameter adjustments[cite: 101], your system is explicitly designed to dynamically swap constraints for different city development plans without altering the core solver, making it vastly more robust for real-world architecture.

**_ Reference Number: 2 _**

# Literature Review Extraction: Computer-Generated Residential Building Layouts

## Context

The authors address the problem of automated generation of residential building layouts with cohesive interiors, primarily targeting computer graphics applications such as video games and social virtual worlds. The goal is to produce visually plausible internal organizations of spaces from minimal, high-level user requirements rather than strict architectural or engineering blueprints.

## Approach

The methodology follows a data-driven, two-stage pipeline inspired by real-world architectural design:

1. **Architectural Programming (Bayesian Networks):** Expands high-level inputs (e.g., number of rooms, total square footage) into a complete "architectural program" (a list of rooms, desired sizes, and graph-like adjacencies). This is generated by sampling a Bayesian network trained on 120 real-world floor plans.
2. **Floor Plan Optimization (Stochastic Optimization):** Converts the architectural program into a 2D floor plan using the Metropolis algorithm (simulated annealing). It starts with a grid of rectangles and iteratively applies proposal moves (sliding walls, snapping walls, swapping rooms) to minimize a heuristic cost function based on accessibility, room dimensions, cross-floor support, and shape convexity.
3. **3D Generation:** Extrudes the 2D layout into a complete 3D model with customized architectural styles, applying rules for doors, windows, and roofs.

## Evidence

- **Performance:** The Metropolis optimization algorithm resolves a layout in approximately 35 seconds on an Intel Core i7 (3.2GHz).
- **Training Time:** Bayesian network training ranged from ~24 minutes (single-story) to ~138 minutes (three-story).
- **Outputs:** Successfully generates diverse, multi-story floor plans with non-convex/rectilinear rooms and functional internal circulation (hallways, doors), matched with external 3D architectural styles (e.g., Tudor, Craftsman).

## Critique

- **Heuristic/Soft Constraints:** The optimization uses a penalty-based cost function rather than hard mathematical constraints. As a result, it is not guaranteed to find a global optimum.
- **Failure Rates:** The stochastic optimization occasionally terminates before resolving critical accessibility, resulting in blocked staircases or inaccessible rooms (fails in ~5% of two-story and 20% of three-story layouts).
- **Lack of Real-World Engineering:** The model is highly idealized for graphics and entirely ignores site-specific constraints, local climate, structural stability, and building regulations.

## Comparative Analysis against Completed Project

**Overlaps & Similarities:**

- **2-Stage Generation Process:** Both projects utilize a bifurcated approach—generating a graph-like skeleton/relationship network first, followed by the actual spatial layout generation.
- **Holistic Spatial Generation:** Both explicitly model room placement, realistic adjacencies, internal circulation, and the placement of doors and windows.
- **Rectilinear Shapes:** Both move beyond basic rectangular packing. While this paper uses wall-splitting and snapping during the Metropolis optimization to achieve concavities, the user's project achieves this via CP-SAT solver generation followed by a post-processing wall-extension technique.
- **Interactive Performance:** Both achieve rapid generation times on consumer-grade hardware (35 seconds for this paper; 1–3 minutes for the user's project).

**Gaps & Where This Paper Falls Short (User Project Advantages):**

- **Solver Methodology:** The paper uses stochastic optimization (Metropolis algorithm) which leads to the edge-case failures mentioned above. The user's project utilizes Google OR-Tools CP-SAT Solver and Optuna, ensuring deterministic satisfaction of constraints.
- **Strict Regulatory Compliance (SP 2):** This is the most significant gap. The paper optimizes for "visual plausibility" using soft penalties. The user's project enforces actual Sri Lankan building regulations (setbacks, minimum room sizes) as hard mathematical constraints, making it viable for real-world construction planning.
- **Target Audience & UI (SP 1):** The paper targets graphics programmers and automated procedural generation pipelines. The user's project is specifically designed with a simple web interface aimed at non-technical private landowners.
- **Extensibility (SP 5):** The paper's Bayesian network requires extensive retraining on new datasets to change architectural behaviors. The user's project allows for highly modular, dynamic constraint modification for different city development plans without altering the core solver.

**_ Reference Number: 3 _**

# Literature Review Extraction: Floor Plan Generation as an Optimization Problem

## Context

The research aims to assist architects during the early sketching and design stages of residential projects by procedurally generating a diverse set of floor plans. The author notes that while procedural content generation (PCG) is popular in virtual world creation, architectural software rarely incorporates procedural techniques. The goal was to build a system that takes core project schematics (plot area, number of rooms, and desired connections) and outputs usable, highly variable design ideas without restricting the generation to a predefined rectangular outer shape.

## Approach

- **Core Algorithm:** Simulated Annealing (SA), a probabilistic optimization technique used to explore the problem space and reach global maximums by occasionally accepting worse states to escape local optimums.
- **Data Representation:** The available plot space is mapped to a 2D modular grid (40cm cell width).
- **State Mutation:** The layout is generated by applying three simple move types to room boundaries: Add Cell, Remove Cell, and Steal Cell (taking an adjacent cell from a neighboring room).
- **Evaluation (Fitness Function):** The SA algorithm evaluates states using a weighted sum of 9 penalty/reward parameters: minimum/maximum size, room ratio (rectangularity), average distance between rooms, shape simplicity (penalizing non-rectangular shapes), connectivity (rewarding desired adjacencies), bounding box limits, and penalties for one-cell-wide corridors or internal holes.

## Evidence

- **Testing Setup:** The method was tested on three house types with varying complexity: House Type 1 (7 rooms), House Type 2 (10 rooms), and House Type 3 (14 rooms). 10 floor plans were generated per type.
- **Performance Metrics:** The SA algorithm ran for approximately 3 million iterations per floor plan.
- **Time:** The generation proved to be highly computationally expensive, taking an average of 62 minutes for Type 1, 55 minutes for Type 2, and 98 minutes for Type 3.
- **Output Quality:** The system successfully generated highly diverse layouts (verified via a custom "distance" metric between generated plans). However, qualitative evaluation revealed that most outputs required manual intervention (1 to 3 "moves" by an architect) to become perfectly logical.

## Critique

- **Performance Bottleneck:** The method is exceptionally slow (roughly an hour per layout), making it entirely unsuitable for interactive, real-time, or rapid iterative use. The bottleneck scales heavily with the grid resolution.
- **Constraint Violations:** Because Simulated Annealing relies on a weighted fitness function (soft constraints), there is no mathematical guarantee that strict requirements (like absolute minimum room sizes or exact connections) are met. The algorithm frequently settles on layouts that slightly violate user inputs if the overall "score" is acceptable.
- **Inconsistent Quality:** The stochastic nature of the cell-growth method sometimes results in jagged, stair-like room shapes, illogical layouts, or unnecessarily long "arms" branching off rooms.
- **Complexity Scaling:** The research demonstrates that as the number of rooms and connections increases, the overall quality of the layout degrades, and the distance from the ideal target metrics widens.

## Comparative Analysis against Your Project

**Where the Paper Overlaps with Your Project:**

- **Graph-based Relationships:** Both projects utilize a connectivity/adjacency graph as the foundational requirement for routing the floor plan logic.
- **Non-Rectangular Capabilities:** Both projects move beyond simple square bounding boxes to generate realistic rectilinear layouts, though the methods differ (theirs via grid-cell aggregation, yours via post-processing wall extensions).
- **Circulation Modeling:** Both projects factor in hallways, though the paper handles hallways simply as another room type with different rectangularity penalties, rather than dedicated routing entities.

**Where Your Project Surpasses or Differs from the Paper:**

- **Target Audience & Interface (SP1):** The paper explicitly builds a tool _for architects_ to aid in professional drafting. Your focus on non-technical private landowners with a simple web interface fills a distinct accessibility gap in the literature.
- **Solver Methodology (TF1, TF2, TF3):** The paper relies on Simulated Annealing on a grid, a stochastic, single-stage mutation process. Your methodology is far more sophisticated, using Optuna for sampling and Google OR-Tools (CP-SAT) for a deterministic, two-stage generation process.
- **Strict Regulatory Compliance (SP2):** This is a major differentiator. The paper's use of a fitness function means constraints are _soft_ (penalized, but allowed). Your use of CP-SAT allows for _hard_ mathematical constraints, guaranteeing that building regulations (like Sri Lankan setback laws and minimum room sizes) are strictly enforced without exception.
- **Performance & Interactivity (SP4):** The paper's method requires 1 to 1.5 hours to generate a single layout. Your generation time of 1-3 minutes on consumer hardware represents a massive leap in efficiency, fundamentally enabling the interactive web-based UX you are targeting.
- **Holistic Spatial Generation (SP3):** While the paper models wall adjacency, it explicitly leaves out the generation of doors and windows, assuming an opening can exist if two rooms share a wall. Your explicit modeling of doors and windows creates a much more complete and realistic architectural artifact.
- **Extensibility (SP5):** While the paper's fitness weights can be tweaked, your dynamic constraint modification architecture allows for entirely different city development plans to be swapped in seamlessly, making your system more robust for real-world regulatory environments.

**_ Reference Number: 4 _**

# Literature Review Extraction: Space Plan Generator (Das et al., 2016)

## Context

The authors address the problem of architectural space planning being severely constrained by tight deadlines, which limits the exploration of design solutions and impedes optimal decision-making. The project aims to automate the rapid generation and evaluation of space plan layouts to free up architects' time for problem formulation and assist stakeholders in making informed, goal-driven decisions. The primary case study focuses on a highly constrained healthcare design project (a hospital bed tower).

## Approach

The methodology relies on procedural generation and computational geometry, structured as a Dynamo plugin (C#) consisting of a "Generator" and an "Analyzer." Key concepts include:

- **Hierarchical Space Assignment:** A top-down approach that allocates spaces in the order of site $\rightarrow$ departments $\rightarrow$ programs (rooms) $\rightarrow$ circulation.
- **K-dimensional (K-d) Tree Data Structure:** Used to partition the site space into a binary search tree. This structure facilitates spatial splitting, nearest-neighbor searches (to build topology maps), and evaluation of departmental adjacencies.
- **Cell Grid & Pathfinding:** Overlays an orthogonal cell grid on the site bounding box. Cells are weighted for specific metrics (e.g., daylighting, acoustics). Dijkstra’s Algorithm is used on a cell neighbor matrix to compute shortest paths for circulation networks and to locate access points (doors/windows).
- **Procedural Splitting Strategies:** Employs algorithms to slice spaces by distance, ratio, area, or recursive minimum dimensions, toggling between horizontal and vertical splits (slice-and-dice).
- **Deferred Geometry:** Geometry is only rendered at the very end of the process for visualization; all intermediate generation relies strictly on numerical/data structures to improve computational speed.

## Evidence

The system was successfully deployed to generate and score hundreds of design options for a healthcare facility case study. It produced distinct floor plans that were scored across parameters such as Program Fitted Score, External View Score, Travel Distance Score (e.g., nurse travel routes), and Key Planning Unit (KPU) Proportion. The separation of geometry from computation allowed the system to generate and analyze space plans iteratively in real-time as the user adjusted parameters via sliders.

## Critique

- **Orthogonal Limitations:** The system struggles with non-orthogonal or curved spaces. It relies on forcing an orthogonal bounding box onto arbitrary site outlines.
- **Single-Story Constraint:** The current iteration is restricted to single-floor designs to maintain stability and reliability; it cannot natively stack spaces or distribute programs across multiple levels.
- **Lack of Learning Mechanism:** The procedural system generates options based on input parameters but does not learn from previous iterations. The authors note this can sometimes lead to architecturally inadequate or "wasteful" proposals, identifying a future need to couple the system with Genetic Algorithms (GA) for true optimization.

## Comparative Analysis against Completed Project

**Technical Features Comparison:**

1.  **Solver vs. Procedural Trees:** While your project utilizes the Google OR-Tools CP-SAT solver to enforce hard mathematical constraints, this paper relies on a procedural K-d tree splitting algorithm. Their approach is generative rather than strictly constraint-satisfying.
2.  **Sampling/Learning:** Your use of Optuna for initial sampling provides an optimized starting point. The Das paper explicitly lacks an iterative learning or sampling mechanism, relying on brute-force procedural generation and relying on the user to filter outputs based on computed scores.
3.  **Generation Stages:** Your 2-stage (skeleton graph $\rightarrow$ floor plan) approach differs fundamentally from their hierarchical (site $\rightarrow$ department $\rightarrow$ program) bounding-box splitting approach.
4.  **Post-Processing Shapes:** You use a post-processing step to extend walls and convert rectangles to rectilinear shapes. Das et al. use "Cell-grid merging" and "notch removal" to refine building outlines, arriving at a somewhat similar goal of non-rectangular building footprints, but via grid-based voxel merging rather than constraint relaxation.

**Selling Points Comparison:**

1.  **Target Audience:** This is a major divergence. Your project targets non-technical private landowners via a simple web interface. The Das paper is highly technical, built as an Autodesk Dynamo plugin targeting expert medical planners and architects requiring complex `.csv` program documents.
2.  **Regulatory Compliance vs. Performance Metrics:** Your system strictly enforces Sri Lankan building regulations (setbacks, minimum sizes) as hard constraints. The Das paper focuses on "soft" performance metrics (nurse travel distance, daylighting views) and uses constraints primarily for internal space fitting rather than external municipal law.
3.  **Holistic Spatial Generation:** Both projects successfully generate holistic environments. Like your project, Das et al. explicitly model rooms, circulation, doors, and windows (using Dijkstra's algorithm on a cell grid for the latter elements).
4.  **Interactive Performance:** Both systems achieve high performance. You achieved 1-3 minute generation on consumer hardware using CP-SAT; Das et al. achieve near real-time generation by entirely separating geometry from computation until the final visualization step.
5.  **Extensibility:** Your system allows dynamic constraint modification for different city plans without altering the core solver. Das et al.'s system is modular by virtue of being a Dynamo visual programming graph, but adapting it to entirely new domains (beyond the healthcare K-d tree logic) requires structural graph reconfiguration by an expert.
6.

**_ Reference Number: 5 _**

**Context:**
Addresses the combinatorial explosion inherent in manual floor plan design by automating the exhaustive generation of all geometrically valid rectangular layouts. The goal is to provide architects with a systematic, computer-aided exploration of the complete solution space under strict dimensional and topological constraints.

**Approach:**

- **Algorithm:** Recursive depth-first tree search (backtrack programming) on a congruent-cell modular grid.
- **Core Workflow:**
  1. Computes valid "cell distributions" based on room area limits and a "modular simplicity" criterion (minimizing grid cells in the smallest room).
  2. Generates compatible room rectangles and grid dimensions.
  3. Composes tight rectangular mosaics via recursive allocation.
  4. Enforces topological constraints using a custom logical formalism ("topological formulas") mapped to constraint graphs.
  5. Computes valid rectangle positions using geometric set intersections and enforces a strict allocation ordering rule to maintain "constraint invariance."
- **Implementation:** Pascal-based prototype executing on 1970s/80s mainframe architecture.

**Evidence:**

- Successfully solved realistic residential problems up to 10 rooms.
- 9-room dwelling (5-person house): Generated 22 valid solutions in ~2 minutes CPU time (UNIVAC 1100/82).
- 10-room problem: 6 solutions in 8.7s CPU time.
- 7-room problem: 69 solutions in 5.5s CPU time.
- Performance heavily dependent on topological constraint strength, room allocation sequence, and modular complexity (`m`). Lower `m` yielded significantly faster runtimes.

**Critique:**

- **Geometric Limitation:** Strictly limited to tightly packed rectangular mosaics. Cannot natively produce rectilinear or complex polygonal rooms; suggests "pseudo-rooms" as a workaround but lacks formal post-processing.
- **Search Scalability:** Exhaustive backtrack search becomes computationally prohibitive as constraints weaken, room counts exceed ~10, or modular complexity increases. Not economically feasible for high-complexity or open-constraint problems.
- **Constraint Rigidity:** Topological formulas must be acyclic and follow a strict allocation order. Cyclic dependencies or poorly ordered inputs break the generation process.
- **Architectural Detail Gap:** Lacks explicit modeling for doors, windows, circulation networks, or structural elements. Daylight/entry is approximated via exterior wall adjacency only.
- **No Optimization Layer:** Purely constraint-satisfaction based; does not rank or optimize solutions based on cost, flow, or desirability.

**Comparative Analysis (vs. Your Project):**
_Overlaps & Addressed Concepts:_

- **Strict Hard Constraints:** Like your project, it enforces hard mathematical bounds for room areas, minimum side extensions, and minimum shared wall lengths, ensuring regulatory-like dimensional compliance.
- **Holistic Adjacency/Circulation Modeling:** Explicitly handles room adjacency and circulation implicitly by treating hallways as constrained rooms with topological formulas, aligning with your spatial relationship modeling.
- **Generation Performance:** Achieves 1–3 minute generation times for ~9–10 room problems, matching your target interactive performance window.
- **Constraint Formalism:** Uses structured topological logic to define spatial relationships, conceptually similar to your graph-like skeleton generation stage.

_Gaps & Where Your Project Surpasses It:_

- **2-Stage Architecture vs. Monolithic Search:** Your decoupled approach (graph skeleton → CP-SAT geometry) avoids the combinatorial explosion and ordering rigidity of this paper's single-stage exhaustive search, offering superior scalability and predictability.
- **Rectilinear Post-Processing:** This paper is strictly rectangular. Your post-processing wall-extending step transforms rectangles into realistic rectilinear rooms, directly solving a major architectural realism gap present in this work.
- **Modern Solving Paradigm:** Uses 1980s backtracking instead of Google OR-Tools CP-SAT and Optuna sampling. Your stack inherently handles cyclic constraints better, supports optimization/objectives, and leverages heuristic initialization for faster convergence.
- **Explicit Doors/Windows & Regulatory Framework:** The paper only approximates entry/daylight via exterior adjacency. Your project explicitly models doors, windows, and hardcodes actual Sri Lankan building regulations, providing far stricter and more realistic compliance.
- **User Accessibility & Modularity:** The paper is purely algorithmic with no UX consideration. Your focus on non-technical landowners via a simple web UI, combined with dynamic constraint modification for different city plans, makes your system significantly more modular, extensible, and market-ready.

**_ Reference Number: 6 _**

**Context:**
Addresses the high cost of manual interior modeling for games/virtual environments by procedurally generating building floor plans. Specifically targets the lack of designer control over room topology and the failure of existing methods to guarantee architectural consistency constraints like reachability and connectivity.

**Approach:**

- Hierarchical layout decomposition into functional zones (public/private) followed by individual rooms.
- Grid-based placement using a weight matrix influenced by adjacency constraints and estimated room size ratios.
- Three-phase constrained growth algorithm: (1) Rectangular expansion prioritizing maximum linear space, (2) L-shaped expansion to utilize remaining irregular space while avoiding U-shapes, (3) Gap-filling for residual empty cells.
- Post-processing connectivity algorithm that places interior doors based on public/private room hierarchy and explicit connectivity constraints.
- Multi-floor support via fixed staircase/elevator room duplication across levels.

**Evidence:**

- Generates simple rectangular layouts in 100 ms and complex L-shaped villa floor plans in ~1 second.
- Produces multiple valid solutions per execution, enabling random selection or heuristic ranking (e.g., minimizing hallways/corners).
- Visually validated against real-world North-American residential plans and iteratively refined using architect feedback.
- Successfully maintains reachability, adjacency, and multi-floor connectivity across tested examples.

**Critique:**

- Door placement on shared walls is randomized within selected segments, frequently resulting in suboptimal internal circulation paths.
- Lacks explicit dimensional constraints for specific room types, leading to impractical configurations (e.g., L-shaped garages).
- Grid-based foundation inherently restricts support for arbitrary angles or rotated building footprints without algorithmic extension.
- Heuristic solution-scoring mechanism is underdeveloped.
- Less effective for highly regular, structured environments (e.g., office buildings) where specialized subdivision methods outperform it.

**Comparative Analysis:**

- _Technical Features Overlap/Contrast:_
  - Both models adjacency, connectivity, circulation, and door placement. Both ultimately produce rectilinear/L-shaped rooms.
  - The paper relies on a fast, heuristic grid-growth algorithm (<1s) vs. your CP-SAT + Optuna pipeline (1-3 min). Your constraint-solver foundation provides stricter topological and dimensional guarantees than the paper's probabilistic growth.
  - Your 2-stage graph-skeleton approach offers explicit structural control before geometry generation, whereas the paper's hierarchical zones grow organically without an explicit relational graph phase.
  - Your post-processing wall extending systematically converts rectangles to rectilinear shapes with precise control; the paper's growth natively creates L-shapes but cannot enforce specific room proportions or hard dimensional bounds.
- _Selling Points Overlap/Contrast:_
  - _Regulatory Compliance:_ The paper enforces only topological adjacency/connectivity constraints. It lacks hard mathematical enforcement of real-world regulations (setbacks, minimum room sizes), which is a core differentiator of your system.
  - _Target Audience & Interface:_ Designed for game developers seeking rapid asset variation, not for non-technical private landowners. No web interface or accessibility features are mentioned.
  - _Holistic Spatial Generation:_ Both explicitly model rooms, hallways, and doors. However, your system's integration of windows, circulation, and regulatory constraints into a single solver pipeline offers higher architectural realism than the paper's entertainment-focused heuristic.
  - _Performance vs. Rigor:_ The paper prioritizes speed (<1s) over strict constraint satisfaction. Your 1-3 minute generation time reflects the computational cost of solving hard regulatory constraints via CP-SAT, a necessary trade-off for real-world applicability.
  - _Modularity:_ The paper's constraints are statically defined per generation run. Your dynamic constraint modification system allows seamless adaptation to varying city development plans without core solver alterations, offering superior extensibility for urban planning use cases.

**_ Reference Number: 8 _**

### Context

The paper addresses the procedural generation of 2D interior floor plans for buildings with predefined, arbitrary (including non-convex) exterior boundaries. The core problem is to automatically satisfy user-defined architectural requirements (room counts, types, dimensions, and adjacencies) and exterior features (walls, windows, doors) while avoiding computationally expensive stochastic optimization steps typical in prior work.

### Approach

Utilizes a heuristic, growth-based procedural generation pipeline:

1. **Irregular Grid Construction:** Generates an axis-aligned grid by extending lines from exterior reflex angles, window midpoints, and recursively splitting walls longer than a threshold `tW`.
2. **Eligible Cell Identification:** Selects grid cells for room seeding based on a distance threshold `tD`, prioritizing cells containing exterior features.
3. **Probabilistic Placement:** Places rooms sequentially using a multi-factor scoring system (window presence, social/private proximity to entrance, elastic/hard connection rules, entrance door compatibility). Scores are normalized to probabilities for stochastic selection.
4. **Iterative Expansion:** Grooms rooms in three phases: (a) expansion to minimum required size, (b) a "fixing step" that contracts adjacent rooms to unblock undergrown rooms, and (c) secondary expansion to fill remaining space while preserving connectivity to the entrance.
5. **Implicit Circulation:** Unclaimed grid cells automatically become corridors. No explicit connection graph or mathematical solver is used.

### Evidence

- **Qualitative:** Generated layouts demonstrate comparable room topology and proportional area distribution to manually drafted architect plans.
- **Quantitative:** Tested across 17 building outlines with varying room/connection constraints (1,000 runs per case). Execution times average 1–5 milliseconds per successful generation. Success rates range from 0% to 100%, heavily dependent on the ratio of user requisites to available grid cells and building footprint size. Failure modes are tracked across three categories: placement errors (no eligible cells), expansion errors (insufficient space for minimum size), and connectivity errors (rooms blocked from entrance).

### Critique

- **Unrealistic Layouts:** The probabilistic/heuristic approach frequently produces valid but spatially impractical results (e.g., exterior-facing corridors, U-shaped circulation zones, disproportionately small bathrooms, odd room aspect ratios).
- **Geometric Rigidity:** Strictly confined to axis-aligned rectangular rooms; cannot natively process diagonal/curved walls or generate rectilinear/non-rectangular room shapes.
- **Implicit Corridors:** Lacks explicit circulation modeling; hallways are merely leftover grid cells, leading to inefficient or awkward flow.
- **No Constraint Guarantees:** The algorithm frequently fails entirely if initial placement or growth paths become blocked, or if requisites exceed spatial capacity. It lacks backtracking or global optimization to recover from local failures.
- **Limited Scope:** Designed for single-floor generation only. Does not incorporate formal building codes, setbacks, or regulatory compliance metrics.

### Comparative Analysis

**Overlaps with Your Project:**

- Explicitly models room placement, adjacency, windows, doors, and circulation within predefined building footprints.
- Handles non-convex exterior polygons.
- Prioritizes rapid generation suitable for interactive or real-time applications.

**Gaps & Shortcomings vs. Your Project:**

- **Solver & Architecture:** Relies on heuristic scoring and local growth rather than your CP-SAT + Optuna 2-stage graph-to-geometry pipeline. Lacks mathematical guarantee of constraint satisfaction and explicit relationship graph generation.
- **Regulatory Compliance:** Uses basic user-defined size/type heuristics instead of hard-coded, real-world building regulations (e.g., Sri Lankan setbacks/codes). Cannot enforce strict legal constraints as mathematical bounds.
- **Post-Processing & Geometry:** Outputs strictly axis-aligned rectangles. Completely lacks your post-processing wall extension step that converts basic rectangles into realistic rectilinear room shapes.
- **Circulation Modeling:** Generates hallways implicitly as leftover space, whereas your project explicitly models circulation as a first-class structural component.
- **Target Audience & Extensibility:** Purely algorithmic with no UI or non-technical user consideration. Adding new constraints requires modifying scoring/expansion logic, making it less modular than your CP-SAT-based system where constraints can be dynamically swapped without altering the core solver.
- **Performance Trade-off:** Generates plans in milliseconds (vs. your 1–3 mins), but sacrifices constraint fidelity, geometric realism, regulatory compliance, and reliability to achieve raw speed. Your project's longer runtime is a direct trade-off for deterministic constraint satisfaction and higher architectural quality.

**_ Reference Number: 9 _**

# Literature Review Extraction: Floor Plan Generation via Squarified Treemaps

**Context**
The research addresses the procedural generation of residential floor plans for virtual environments and games. The core problem tackled is ensuring that automatically generated interiors are functionally coherent, geometrically compact, and fully navigable, with all rooms accessible from the outside or via internal connections, while embedding semantic data for virtual agent simulation.

**Approach**

- **Core Algorithm:** Adapts the Squarified Treemaps algorithm (a space-filling hierarchical visualization technique) to recursively subdivide a building footprint into rectangular rooms while optimizing aspect ratios toward 1:1.
- **Zoning Pipeline:** First partitions the total area into three functional zones (social, service, private) using treemaps, then recursively applies treemaps within each zone to define individual room geometries.
- **Connectivity & Circulation:** Assigns doors/windows based on a static adjacency matrix derived from common architectural patterns. Resolves isolated rooms by constructing a graph from remaining internal wall segments and applying the A\* pathfinding algorithm to compute a minimal "corridor backbone" that links all disconnected spaces.
- **3D Extrusion & Semantics:** Extrudes the finalized 2D layout to a user-defined height, cuts openings for doors/windows, and attaches semantic tags (room function, agent behavior hints) to support downstream simulation.

**Evidence**

- Successfully generates varied, realistic rectangular floor plans with guaranteed full connectivity after corridor insertion.
- Demonstrates functional parity with real-world architecture by comparing a generated 84m² layout to a commercial 94m² house, noting nearly identical room size distributions and connectivity graphs.
- Supports dynamic, parameter-driven generation (randomized room counts/areas) suitable for real-time game engine integration.
- Semantic tagging enables direct use in virtual human navigation and behavioral animation pipelines.

**Critique**

- **Geometric Rigidity:** Inherently produces strictly rectangular footprints and rooms due to the treemap foundation; cannot represent L-shaped, U-shaped, or other rectilinear room geometries common in real architecture.
- **Static Rule Dependency:** Connectivity relies on a hardcoded adjacency table rather than dynamic spatial reasoning or constraint optimization, limiting architectural diversity.
- **Corridor Artifacts:** A\* pathfinding on wall-segment graphs can yield unnatural corridor angles and may shrink adjacent rooms below minimum viable areas, triggering manual or heuristic global readjustments.
- **Lack of Environmental/Regulatory Context:** Ignores site-specific constraints (setbacks, solar orientation, topography, municipal codes) and focuses purely on internal partitioning.
- **Unquantified Performance:** Claims "real-time" generation but provides no computational benchmarks, hardware specs, or scalability limits.

**Comparative Analysis (vs. Completed Project)**

- **Overlap/Shared Goals:** Both systems procedurally generate functional residential layouts with explicit room placement, circulation pathways (hallways/corridors), and door/window placement. Both prioritize full spatial accessibility and embed metadata for downstream simulation/use.
- **Methodology Gap:** Relies on heuristic space-partitioning (Treemaps + A\*) rather than constraint-based optimization. Cannot enforce hard mathematical constraints (e.g., exact minimum room areas, setback rules, or regulatory compliance), which your CP-SAT + Optuna pipeline explicitly handles.
- **Geometric Limitation:** Produces only axis-aligned rectangles. Lacks your post-processing wall extension step that transforms rigid rectangles into realistic rectilinear room shapes.
- **Workflow Difference:** Uses a single-pass subdivision + corridor repair loop. Does not employ your 2-stage architecture (graph-like skeleton generation → geometric realization), which offers finer control over adjacency before committing to coordinates.
- **Target & Usability:** Geared toward graphics/game development pipelines with no interface for non-technical users. Lacks your simple web-based UI and focus on private landowners without architectural expertise.
- **Modularity/Extensibility:** Adjacency and zoning rules are static/hardcoded. Contrasts with your modular constraint framework that allows dynamic adaptation to different municipal development plans without altering the core solver.
- **Performance Benchmarking:** Vague "real-time" claims vs. your documented 1–3 minute generation window on consumer hardware, providing a concrete, reproducible performance baseline for practical deployment.

**_ Reference Number: 11 _**

**Context:** Addresses the challenge of generating floor plans for large, complex public buildings where room programs and building footprints are initially undefined. Focuses on automating non-standardized layouts with intricate connectivity (corridors, halls, foyers, vertical cores), a task traditionally time-consuming and requiring expert architectural knowledge.

**Approach:** Utilizes a custom, square-grid heuristic algorithm paired with a quasi-evolutionary iteration strategy. The "Magnetizing" method begins by constructing an evacuation-like corridor network to ensure all rooms are accessible. Rooms are placed sequentially, prioritizing the most adjacency-constrained spaces first within a proximity threshold to existing corridors. An iterative backtracking mechanism runs multiple generations, evaluates them by placed room count/total area, and refines top branches by backtracking 1–5 placements before continuing. Post-processing removes corridor dead ends, adjusts to site boundaries, and inserts halls/foyers. Inputs are managed via a Grasshopper/Rhino visual programming environment using custom `HouseInstance` and `RoomInstance` components.

**Evidence:** Generates complete or near-complete layouts fitting within specified boundaries in seconds to minutes. Successfully produces diverse variants from the topological structure of iconic buildings. Early user feedback confirms the Grasshopper interface is intuitive for managing complex room programs and topological relationships, with users reporting ease in tweaking parameters for their specific projects.

**Critique:** Relies on a simplified assumption that all rooms must connect through a single, interlinked corridor network, ignoring direct room-to-room adjacencies or shared/implicit spaces. Struggles with multi-floor continuity, complex boundary fitting (often leaving unintentional corners/edges), and the geometric restrictions of a rigid square grid. The quasi-evolutionary iteration scales poorly as complexity increases, requiring further optimization. Remains a developmental prototype rather than a production-ready system.

**Comparative Analysis:**

- **Overlaps:** Both projects separate topological relationship mapping from geometric placement (graph-like skeleton vs. evacuation-like corridor network). Both target rapid generation times (seconds/minutes vs. 1–3 minutes). Both employ iterative optimization (quasi-evolutionary backtracking vs. Optuna sampling) and incorporate post-processing to refine initial outputs. Both explicitly model room adjacency and circulation networks as foundational layout drivers.
- **Gaps & Shortcomings vs. User Project:**
  - _Solver & Constraints:_ The paper uses custom grid heuristics rather than a formal constraint satisfaction solver (CP-SAT). It lacks hard mathematical constraint enforcement, making it incapable of handling strict regulatory compliance (setbacks, minimum room sizes) or dynamic constraint modification.
  - _Target Audience & Interface:_ Targets architectural professionals via Grasshopper, contrasting with the user’s simple, web-based interface designed for non-technical private landowners.
  - _Spatial Detail & Post-Processing:_ Sticks to grid-based cells and omits doors, windows, and rectilinear room shaping. The user’s wall-extending post-processing directly resolves this limitation, transforming rectangle-only outputs into realistic rectilinear layouts.
  - _Extensibility & Multi-Floor:_ Multi-floor handling and complex boundary adaptation are explicitly noted as unresolved limitations in the paper. The user’s modular architecture allows seamless constraint updates for different city development plans without altering the core solver, a capability the paper's heuristic framework lacks.

**_ Reference Number: 12 _**

## Literature Review Extraction: Shekhawat (2014) - Spiral-Based Rectangular Floor Plan Algorithm

### Context

- **Problem**: Arranging a finite collection of rectangular spaces of varying sizes inside a rectangular frame while optimizing for _connectivity/adjacency_—a criterion often overlooked in prior floor plan literature.
- **Secondary Goal**: Systematically introduce and manage "extra spaces" (waste/circulation areas) to maintain rectangular composition under geometric/topological constraints.

### Approach

- **Core Algorithm**: Spiral-based rectangular floor plan (RSF) algorithm.
- **Placement Strategy**: Spaces sorted by increasing area; placed sequentially in a clockwise spiral pattern (left → above → right → below) around a growing composite rectangle.
- **Dimension Calculation**: Fibonacci-inspired recursive sequence to compute composite width/height after each placement.
- **Adjacency Modeling**: Two rectangles are adjacent if they share a wall or sub-wall; adjacency graph constructed with spaces as vertices and shared boundaries as edges.
- **Theoretical Guarantee**: Proven that RSF(n) achieves exactly 3n–7 edges in its adjacency graph for n>3, which is the theoretical maximum for any rectangular floor plan—thus "optimally connected."
- **Variants**: Seven additional RSF configurations via anticlockwise spirals or altered initial placements.

### Evidence

- **Theoretical**: Mathematical proofs establishing the 3n–7 edge bound for RSF and the upper limit for any rectangular floor plan.
- **Demonstrative**: Step-by-step construction example with 5 spaces (bedroom, kitchen, bathroom, WC, living room); adjacency graphs generated for all 8 spiral variants.
- **No empirical metrics**: No computational performance data, user studies, or real-world case validations provided.

### Critique / Limitations

- **Shape Restriction**: Exclusively handles axis-aligned rectangles; no support for rectilinear, L-shaped, or irregular rooms.
- **Extra Space Handling**: Generates unavoidable waste/circulation spaces but offers no mechanism to minimize or strategically allocate them (acknowledged as future work).
- **Constraint Vacuum**: Ignores real-world architectural constraints: building codes, setbacks, door/window placement, minimum room dimensions, or regulatory compliance.
- **Connectivity Metric**: Measures connectivity solely by edge count in adjacency graph; does not evaluate practical circulation quality, privacy, or functional adjacency preferences.
- **Deterministic & Single-Objective**: No optimization framework for multi-objective trade-offs (e.g., area efficiency vs. connectivity); no stochastic sampling or solution exploration.
- **Scalability Unknown**: No analysis of computational complexity or performance with increasing space counts.
- **User Interaction Absent**: Purely algorithmic; no consideration of interface, usability, or non-expert user needs.

### Comparative Analysis vs. User Project

#### Overlaps / Shared Concerns

- Both prioritize adjacency/connectivity as a core design criterion.
- Both generate floor plans from a set of required spaces with explicit handling of circulation/extra areas.
- Both aim for systematic, rule-based generation rather than manual drafting.

#### Gaps / Where User Project Advances

| User Project Feature                                       | Paper Coverage                        | Gap Analysis                                                                                                                                      |
| ---------------------------------------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| **CP-SAT + Optuna solver**                                 | Custom deterministic spiral algorithm | User's approach enables constraint satisfaction, multi-objective optimization, and stochastic exploration; paper's method is fixed and heuristic. |
| **2-stage generation (graph → geometry)**                  | Single-stage spiral placement         | User decouples topology from geometry for greater flexibility; paper tightly couples them.                                                        |
| **Post-processing for rectilinear shapes**                 | Rectangle-only output                 | User supports realistic room shapes; paper cannot model non-rectangular spaces.                                                                   |
| **Sri Lankan regulatory constraints as hard constraints**  | No real-world constraints             | User embeds legal/architectural rules directly; paper is purely geometric.                                                                        |
| **Explicit modeling of doors, windows, circulation paths** | Adjacency only (shared walls)         | User captures finer-grained spatial relationships; paper's adjacency is binary and coarse.                                                        |
| **Target: non-technical private landowners + web UI**      | Theoretical/mathematical audience     | User prioritizes accessibility and usability; paper has no user-centered design considerations.                                                   |
| **1–3 min generation on consumer hardware**                | No performance data                   | User provides practical, interactive performance; paper's computational efficiency is unverified.                                                 |
| **Modular constraint system for city-specific rules**      | Fixed algorithm                       | User's architecture supports dynamic adaptation; paper requires algorithmic modification for new constraints.                                     |
| **Intentional circulation/extra space modeling**           | Extra spaces as geometric byproducts  | User likely optimizes circulation utility; paper treats extra spaces as unavoidable waste.                                                        |

#### Where Paper Offers Unique Value

- **Proven optimal connectivity**: Mathematical guarantee of maximum adjacency edges (3n–7) for rectangular layouts—a theoretical benchmark user's project could reference.
- **Interpretable placement logic**: Spiral pattern offers visual, intuitive understanding of space ordering, potentially useful for explainability.
- **Multiple variant outputs**: Eight spiral configurations from same input provide design diversity without re-optimization.

### Synthesis for Literature Review

This paper establishes a theoretically optimal method for maximizing adjacency connectivity in _rectangular-only_ floor plans via a deterministic spiral-placement algorithm. While it contributes a rigorous graph-theoretic foundation for connectivity evaluation, it lacks practical architectural constraints, shape flexibility, user-centered design, and computational validation. Your project addresses these gaps by integrating constraint programming, regulatory compliance, rectilinear shape support, and interactive performance—positioning it as a practitioner-oriented advancement over purely geometric or theoretical approaches. The paper's 3n–7 connectivity bound may serve as a useful theoretical reference point when evaluating the adjacency quality of your generated layouts.

**_ Reference Number: 14 _**

**Context:**
Automated architectural space layout planning during the schematic design phase to replace manual, repetitive, and time-intensive floorplan generation. The paper addresses the "wicked problem" of allocating functional spaces within a building envelope while balancing competing performance metrics like usable area, circulation efficiency, and daylight access.

**Approach:**

- **Core Algorithm:** Physics-inspired parametric model treating rooms as virtual scalar fields. Space allocation is framed as a competitive cell-assignment problem where grid cells are allocated to the room with the strongest field magnitude, subject to a threshold.
- **Circulation Generation:** Modified Dijkstra’s shortest path algorithm with a path-shortening heuristic to consolidate hallways and minimize total circulation area.
- **Optimization Framework:** Multi-objective evolutionary algorithm (NSGA-II via Wallacei in Grasshopper 3D) iteratively optimizes room positions, field mass parameters, and entrance selections.
- **Evaluation Metrics:** Soft-objective fitness functions maximizing internal area, minimizing overlap penalties, reducing circulation footprint, and minimizing shadow area in habitable rooms.

**Evidence:**

- Generated 134 Pareto-optimal layouts for 4-bedroom houses/penthouses and 167 for 24 apartment units across two building floors.
- Runtime averaged ~40 minutes per population (50 solutions) for houses and 20–40 minutes per unit for apartments at coarse resolutions (5u grid).
- Outputs are fully parametric and directly exportable to Rhino/Grasshopper for further architectural refinement.
- Demonstrated successful balancing of conflicting objectives (e.g., maximizing floor area while minimizing circulation and overlap).

**Critique:**

- **Computational Bottleneck:** Algorithm complexity scales quadratically with grid resolution (O(N²)). Finer grids (e.g., 2/9 m) increase runtime to 2–4 hours, making high-detail generation impractical for iterative design.
- **Lack of Architectural Specificity:** Does not explicitly model wall thicknesses, door placements, or window dimensions. Fenestration is oversimplified by assuming all external walls are fully glazed.
- **Soft Constraint Reliance:** Uses penalty-based objectives rather than hard mathematical constraints, risking infeasible or code-violating layouts without manual intervention.
- **Expert Dependency:** Built exclusively within a professional CAD ecosystem (Grasshopper/Rhino), requiring parametric modeling expertise to configure, run, and interpret results.
- **Aesthetic/Functional Gaps:** May produce unconventional or spatially awkward configurations that require human refinement to meet standard architectural conventions or client preferences.

**Comparative Analysis:**

- **Overlaps with Your Project:** Both systems automate spatial layout generation, handle room adjacency/competition, and optimize circulation networks. The multi-objective optimization concept aligns with handling complex spatial trade-offs.
- **Gaps vs. Your Technical Features:**
  1. _Solver:_ Uses stochastic evolutionary search (NSGA-II) + physics fields instead of deterministic CP-SAT constraint programming + Optuna sampling. Lacks your solver's deterministic constraint-handling precision.
  2. _2-Stage Generation:_ Operates as a single iterative loop; lacks your explicit graph-based skeleton stage before physical layout generation.
  3. _Post-Processing:_ Outputs only rectangular/field-bounded cells. Lacks your wall-extending post-processing that converts rectangles into practical rectilinear room geometries.
- **Gaps vs. Your Selling Points:**
  1. _Non-Technical Audience:_ Tied to professional CAD software with a steep learning curve. Fails to provide the simple, web-based, zero-expertise interface you target.
  2. _Strict Regulatory Compliance:_ Relies on soft penalties/fitness functions. Cannot enforce hard, jurisdiction-specific building codes (e.g., Sri Lankan setbacks, minimum room sizes) as inviolable constraints.
  3. _Holistic Generation:_ Omits explicit modeling of doors, windows, and structural walls. Simplifies daylighting to a blanket external-wall assumption rather than precise fenestration placement.
  4. _Interactive Performance:_ 20–40+ minute generation times significantly exceed your 1–3 minute benchmark. Quadratic complexity prevents real-time or near-real-time feedback.
  5. _Modular Extensibility:_ Constraints and objectives are embedded in a fixed Grasshopper parametric definition. Lacks your dynamic, code-level constraint-swapping architecture for adapting to different municipal planning rules without core system redesign.

**_ Reference Number: 16 _**

## Paper: Customization and generation of floor plans based on graph transformations (Wang et al., 2018)

### Context

- **Problem**: Automatic generation of rectangular floor plans from legacy designs while preserving room adjacency relationships, with capability for user-driven customization and modification.
- **Gap addressed**: Existing methods either fail to retain connectivity, require redundant control vertices, or cannot guarantee adjacency preservation during style-conforming generation.

### Approach

- **Core framework**: Graph Approach to Design Generation (GADG)
- **Key concepts**:
  - Dual graph derivation from IFC-format input to represent room adjacency
  - Properly Triangulated Planar (PTP) graph validation as prerequisite for rectangular dual existence
  - Rectangular Dual Graph (RDG) finding algorithm (extended from Bhasker & Sahni's linear-time method)
- **Transformation rules**:
  - _Addition rule_: Inserts vertices into PTP while maintaining triangulation (max 4 adjacent vertices for internal, max 3 for boundary)
  - _Subtraction rule_: Removes vertices with re-triangulation to preserve PTP properties
- **Constraints supported**: Maximum aspect ratio per room; moving internal rooms to boundary
- **Implementation**: Java/Eclipse SWT; integrated with shape grammar interpreter; GUI for parameter specification

### Evidence

- **Performance**: Linear scaling with room count; <5ms generation time for plans with <10 rooms
- **Constraint overhead**: Aspect ratio constraint adds negligible execution time
- **Output fidelity**: Generated plans preserve exact adjacency/connectivity of input dual graph
- **Case study**: 7-room IFC input produced multiple valid layouts within milliseconds; demonstrated addition-rule workflow for inserting new rooms

### Critique / Limitations

- **Shape restriction**: Only generates strictly rectangular rooms; no support for L-shaped, rectilinear, or irregular room geometries
- **Constraint scope**: Limited to aspect ratio and boundary placement; no support for directional constraints, regulatory setbacks, or minimum area requirements
- **Semantic gaps**: Models adjacency only; does not explicitly represent doors, windows, circulation paths, or functional room semantics
- **Preprocessing dependency**: Requires input graph to be PTP or undergo isolated-vertex removal (e.g., closets treated as attributes)
- **Corner selection constraint**: Four corner vertices must yield cycle-free initial left boundary, requiring user re-selection if violated
- **Scalability note**: Hierarchical organization for large/complex layouts mentioned as future work, not implemented

### Comparative Analysis vs. User Project

#### Overlaps / Shared Concepts

| User Feature                   | Paper Equivalent                 | Notes                                                              |
| ------------------------------ | -------------------------------- | ------------------------------------------------------------------ |
| Graph-based adjacency modeling | Dual graph + PTP representation  | Both use graph structures to encode room relationships             |
| Constraint incorporation       | Aspect ratio, boundary movement  | Paper supports parametric constraints but narrower scope           |
| Two-stage conceptual flow      | Dual derivation → RDG generation | Similar skeleton-to-layout pipeline, though implementation differs |
| User customization interface   | GUI for rule parameters          | Both provide interactive control, though target users differ       |

#### Gaps / Where Paper Falls Short

| User Feature                                 | Paper Status                                             | Implication                                                        |
| -------------------------------------------- | -------------------------------------------------------- | ------------------------------------------------------------------ |
| CP-SAT solver + Optuna sampling              | Uses deterministic RDG algorithm                         | Paper lacks optimization-driven exploration or stochastic sampling |
| Rectilinear room shapes via post-processing  | Rectangular rooms only                                   | Cannot generate non-rectangular geometries; key expressiveness gap |
| Regulatory compliance (setbacks, min. sizes) | No regulatory constraint modeling                        | Not suitable for jurisdiction-specific code enforcement            |
| Explicit doors/windows/circulation modeling  | Adjacency-only representation                            | Less semantically rich; cannot validate egress or accessibility    |
| Target: non-technical private landowners     | Targets designers/architects                             | UI/UX assumptions differ; less emphasis on accessibility           |
| Modular constraint system for city plans     | Extensible but not demonstrated for regulatory variation | Less proven adaptability to diverse planning contexts              |
| 1-3 min generation on consumer hardware      | <5ms for <10 rooms                                       | Paper faster but for simpler outputs; not directly comparable      |

#### Summary Assessment

The paper provides a theoretically grounded, adjacency-preserving method for rectangular floor plan generation with efficient graph transformations. However, it diverges significantly from the user's project in: (1) output geometry expressiveness (rectangular-only vs. rectilinear), (2) constraint modeling depth (parametric vs. regulatory), (3) semantic richness (adjacency-only vs. full spatial elements), and (4) target user profile (professionals vs. private landowners). The paper's strength in connectivity preservation and millisecond-scale generation offers a complementary perspective, but its limitations in practical constraint handling and shape flexibility highlight the novelty of the user's constraint-programming and post-processing approach for real-world regulatory compliance.

**_ Reference Number: 18 _**

**Context:**
Addresses a documented gap in floor plan generation literature, which predominantly focuses on dimensionless layouts confined to rectangular boundaries without internal voids. The study targets the generation of dimensioned floor plans for arbitrary non-rectangular boundaries (including slanted line segments) with the optional inclusion of interior open spaces (atriums).

**Approach:**
Implements a semi-automatic, interactive Python GUI (Tkinter) centered on a recursive dissection method driven by the slicing tree paradigm. Users manually define the outer boundary and interior points for voids. The layout is then partitioned via sequential horizontal or vertical cuts. Each dissection requires explicit user input for the resulting sub-block dimensions. The process iterates until all blocks are manually designated as final rooms. No mathematical optimization, constraint solving, or graph-based adjacency modeling is utilized.

**Evidence:**
Demonstrates functional prototype capabilities through step-by-step generation of multiple layout typologies (rectilinear/slanted boundaries, with/without internal open spaces). Validates geometric flexibility by successfully regenerating historical floor plan topologies (Villa Badoer, Palazzo Della Torre) while preserving documented design constraints such as aspect ratios, area ratios, and symmetry. No quantitative computational metrics, optimization scores, or runtime benchmarks are provided.

**Critique:**
The methodology is fundamentally manual and non-automated, requiring users to dictate both the dissection sequence and exact dimensions for every cut. It is strictly limited to slicing floor plans, inherently excluding complex non-slicing topologies. The system lacks any mechanism for adjacency enforcement, circulation paths, door/window placement, or building code compliance. Layout feasibility and architectural viability depend entirely on user expertise. Scalability to dense, multi-room programs is constrained by high manual interaction overhead, and the absence of automated constraint checking makes it prone to geometrically valid but functionally impractical layouts.

**Comparative Analysis:**

- **Overlaps with Your Project:** Both aim to produce dimensioned layouts and accommodate non-rectangular boundaries with internal voids. Both prioritize accessible interfaces to lower the barrier for non-expert users.
- **Gaps & Shortfalls vs. Your Technical Features:**
  - _Solver/Algorithm:_ Uses manual interactive slicing vs. your automated Google OR-Tools CP-SAT + Optuna pipeline.
  - _Process Architecture:_ Single-step user-driven dissection vs. your structured 2-stage graph-skeleton → layout generation.
  - _Post-Processing:_ Outputs strictly rectangular rooms vs. your automated wall-extension post-processing for rectilinear room shapes.
  - _Topology Constraints:_ Slicing tree restricts output to sliceable layouts vs. CP-SAT's capacity to resolve arbitrary, non-slicing adjacency graphs.
- **Gaps & Shortfalls vs. Your Selling Points:**
  - _Target Audience & Usability:_ Requires architectural intuition for dimensioning every cut vs. your streamlined interface for non-technical landowners.
  - _Regulatory Compliance:_ Zero automated constraint enforcement vs. your hard-coded Sri Lankan building regulations (setbacks, minimum sizes).
  - _Holistic Generation:_ Omits adjacency, circulation, doors, and windows vs. your explicit modeling of all spatial and functional relationships.
  - _Performance:_ Unquantified, fully interactive runtime vs. your 1–3 minute automated generation on consumer hardware.
  - _Extensibility:_ Hardcoded GUI/dissection logic vs. your modular framework allowing dynamic constraint updates without solver modification.

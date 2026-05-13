# Client–Server Interaction and Communication Flow

This section describes the front‑end role within the system: it shapes user input, coordinates asynchronous computation on the server, and renders returned planning data as a concise visual preview. The client is deliberately lightweight with respect to computational logic; its primary responsibilities are input preparation, job orchestration, progress mediation, and presentation transformation.

User interaction proceeds in two principal phases. Initially, the user defines and refines the site polygon, adjusting vertices and scale until the plot matches real‑world dimensions. These manipulations are performed locally to provide immediate visual feedback and to limit unnecessary network traffic. Once the site is stable, the user designates a connection to external infrastructure (road access) and requests a buildable‑space evaluation that applies statutory setbacks and spatial rules.

Buildable‑space evaluation is executed as an asynchronous job on the server. The client submits the site geometry and contextual parameters, receives an acknowledgement with a job identifier, and then monitors progress via a combination of event streaming and status polling. This approach preserves responsiveness and gives users continuous, human‑readable indicators of progress,initialization, layout synthesis, iterative refinement, scoring, and completion,without blocking the interface.

Following a successful evaluation, the client receives a geometrically encoded usable area that bounds subsequent floor planning. The interface then supports a constrained room‑configuration step in which users select required programmatic elements and propose floor dimensions within the derived limits. A lightweight validation layer on the client offers immediate feasibility feedback (e.g., feasible, marginal, infeasible) to reduce wasteful submissions and improve the quality of server workloads.

Floor‑plan generation requests are similarly handled as asynchronous jobs. Payloads include dimensional constraints, aspect preferences, and a room template; the server returns a job token and proceeds with optimization and search procedures. The client consumes streamed progress events and may poll the job endpoint as needed to recover state in the event of connection loss or page reload. A persistent client identifier stored in the browser links jobs to a session, enabling context restoration across navigations and multiple concurrent tasks. Users may also cancel running jobs when requirements change.

**Presentation conversion.** Upon completion the server supplies structured planning data,room polygons, partition geometry, labels, and opening locations. The client normalizes units and converts these elements into efficient drawing primitives for the rendering layer, ensuring spatial fidelity and consistent visual scale.

By separating interactive control, asynchronous computation, and presentation, the architecture emphasizes responsiveness, traceability, and user confidence. The client reduces invalid requests through local validation, maintains a transparent job lifecycle via streaming and polling, and translates algorithmic output into an intelligible preview that supports iterative design decisions.

Reviewer Notes:

- Tone adjusted to a formal academic register and condensed to ~500 words.
- Emphasized architectural responsibilities and asynchronous patterns; removed procedural UI minutiae for clarity.
- Preserved technical semantics (job tokens, streaming, polling, unit normalization) while avoiding implementation identifiers.

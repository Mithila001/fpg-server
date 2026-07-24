# Proposal: Server-Sent Event Streaming for Floor-Plan Generation

## Purpose of This Note

This document describes a proposed direction for implementing Server-Sent Event streaming in the floor-plan generation backend.

It is not intended to be a strict implementation specification or an authoritative file-by-file plan.

The coding agent should first inspect the active:

* generation routes,
* generation service,
* job-management logic,
* generation pipeline,
* multiprocessing or worker boundaries,
* existing SSE implementation, if any,
* shared type system,
* serialization behavior,
* cancellation and timeout handling,
* and current frontend-facing API contracts.

The agent should then create its own implementation plan based on what is actually active in the repository.

The concepts, names, file locations, and component boundaries suggested here may be changed where a different design better fits the current architecture.

---

# 1. Main Objective

Introduce a clean SSE streaming system that allows the backend to send useful generation updates to the client while keeping the streaming footprint inside the generation algorithms and pipeline as small as practical.

The client primarily needs:

1. lightweight progress information,
2. candidate trial previews,
3. completed floor plans that are worth displaying,
4. important generation state changes,
5. terminal success or failure information.

The client does not need detailed internal diagnostics explaining how the solver, scorer, or optimization process reached its result.

The SSE feature should therefore expose useful product-level information rather than developer-level algorithm internals.

---

# 2. Main Architectural Principle

The generation pipeline should publish generation events through a small abstraction.

It should not directly manage:

* HTTP responses,
* SSE formatting,
* FastAPI streaming behavior,
* subscriber connections,
* asynchronous queues,
* throttling timers,
* JSON serialization,
* reconnect behavior,
* or disconnected clients.

Conceptually:

```text
Generation Pipeline
        │
        ▼
Generation Event Publisher
        │
        ▼
Event Dispatch / Throttling
        │
        ▼
Per-Job Event Stream
        │
        ▼
SSE Transport
        │
        ▼
Client
```

The exact layers may be combined or reorganized if the existing project already has suitable abstractions.

The main requirement is that algorithm code should not depend directly on SSE or FastAPI-specific behavior.

---

# 3. Product-Level Streaming Philosophy

A useful rule for deciding whether something belongs in SSE is:

> Stream what the client can display or act on, not how the server internally performed the work.

Examples of information that may be useful to the client:

* the current candidate-search trial number,
* the configured trial limit,
* elapsed generation time,
* configured timeout,
* the candidate hint produced by a trial,
* a newly available floor plan,
* whether a floor plan is usable or presentable,
* whether generation has completed,
* whether generation timed out,
* whether generation failed.

Examples of information that probably should not be exposed through production SSE:

* OR-Tools branch counts,
* solver conflicts,
* constraint diagnostics,
* score evaluator breakdowns,
* geometry debugging information,
* rejected candidate explanations,
* internal exceptions that are not safe or useful to expose,
* detailed pipeline profiling,
* multiprocessing diagnostics.

Those details can remain in logging, tests, developer visualization, or optional internal diagnostic systems.

---

# 4. Progress Model

A generic progress percentage may not accurately represent this pipeline.

Floor-plan generation is iterative, and a successful floor plan may be found at any point. The amount of work remaining cannot always be predicted from the current stage.

The two most meaningful measurable progress dimensions appear to be:

1. candidate trial progress,
2. elapsed time relative to the generation timeout.

A progress payload could therefore expose values such as:

```json
{
  "stage": "candidate_search",
  "trial_number": 42,
  "trial_limit": 100,
  "elapsed_ms": 18342,
  "timeout_ms": 60000
}
```

The frontend may display:

```text
Trial 42 of 100
18.3 seconds of 60 seconds
```

The server does not necessarily need to calculate or promise an overall completion percentage.

A percentage may still be derived by the frontend for specific bounded values, but it should not be presented as an accurate prediction of total generation completion unless the implementation can genuinely support that meaning.

---

# 5. Proposed Event Categories

The final set of events should be based on actual client requirements and active pipeline behavior.

A reasonable starting point is:

```text
progress
candidate_trial
floor_plan
status
completed
error
```

These categories may be represented using enums or discriminated models rather than arbitrary strings.

## 5.1 Progress Event

Provides lightweight bounded progress information.

Possible fields:

```text
stage
trial_number
trial_limit
elapsed_ms
timeout_ms
```

This event should remain small.

## 5.2 Candidate Trial Event

Sent for candidate-search trials that the client should visualize.

The requested minimum information is:

```text
trial number
candidate hint points
```

Possible payload:

```json
{
  "trial_number": 42,
  "candidate_hints": {
    "bedroom_1": {
      "x": 20,
      "y": 40
    }
  }
}
```

The exact hint model should reuse the canonical candidate-search type if one already exists.

It should not duplicate or invent another hint representation only for SSE unless serialization requirements justify a separate transport model.

## 5.3 Floor Plan Event

Sent when a floor plan is available for the client to display.

The plan should contain the completed client-useful form, including openings where required.

Possible payload:

```json
{
  "classification": "usable",
  "generation_number": 3,
  "score": 87.5,
  "floor_plan": {
    "...": "..."
  }
}
```

The floor-plan object should preferably reuse or adapt the existing canonical `FloorPlan` domain model, which already contains rooms, openings, boundary data, identity redirects, and transformations.

The agent should inspect whether that domain model is currently JSON serializable or whether a dedicated API response model is already used.

## 5.4 Status Event

Represents a small, meaningful state change.

Examples:

```text
Candidate search started
Floor-plan generation started
Usable floor plan found
Presentable floor plan found
Generation timeout reached
```

Status events should not become a stream of verbose human-readable logs.

Where possible, the event should contain a typed status code that the frontend can translate into user-facing text.

For example:

```json
{
  "status": "usable_floor_plan_found"
}
```

This is usually preferable to using free-form messages as the primary contract.

## 5.5 Completed Event

A terminal event indicating that no further generation events will be sent for the job.

Possible outcomes:

```text
presentable_plan_found
best_usable_plan_returned
completed_without_plan
cancelled
timeout
```

The terminal payload should make it clear whether:

* a final floor plan is included,
* the client should use the most recently received plan,
* or no acceptable result was produced.

## 5.6 Error Event

Represents a terminal or client-relevant failure.

The error contract should be safe and compact.

Possible fields:

```text
stage
code
message
recoverable
```

Detailed exception traces and internal diagnostics should remain server-side.

---

# 6. Floor-Plan Classification

The pipeline may generate multiple floor plans during one job.

It may be useful to classify them consistently.

Possible classifications:

```text
usable
presentable
final
```

Suggested meaning:

* `usable`: meets the minimum accepted floor-plan score or quality threshold.
* `presentable`: meets the preferred threshold and may allow early pipeline termination.
* `final`: the plan selected as the final response when the generation job ends.

These classifications should be aligned with the active pipeline configuration.

If the current pipeline already has names such as `usable_fpg_score` and `presentable_fpg_score`, the streaming contract should follow the same domain terminology unless there is a strong reason to change it.

The agent should also determine whether one plan can be emitted more than once with different classifications. Unnecessary duplicate transmission should be avoided.

---

# 7. Strongly Typed Event Contracts

Event payloads should be strongly typed and consistent.

Avoid using broad contracts such as:

```python
payload: dict[str, Any]
```

as the main internal event interface.

A more reliable structure would define separate payload types, for example:

```python
ProgressPayload
CandidateTrialPayload
FloorPlanPayload
StatusPayload
CompletedPayload
ErrorPayload
```

Possible implementation choices include:

* Pydantic models,
* dataclasses,
* typed dictionaries,
* or a combination of domain dataclasses and transport models.

The coding agent should choose the approach that best matches the active API and type architecture.

The project already has a centralized shared type package under:

```text
app/algorithms/types_new
```

However, streaming transport types may not necessarily belong inside the algorithm type package.

The agent should decide whether SSE contracts are best placed in:

```text
app/streaming
app/events
app/services/streaming
app/schemas/events
```

or another architecture-consistent location.

The important requirement is to avoid creating conflicting duplicate definitions of floor plans, room types, candidate hints, and job identifiers.

---

# 8. Consistent Event Envelope

Every event should use a consistent outer envelope.

A possible structure:

```json
{
  "sequence": 152,
  "timestamp": "2026-07-24T12:34:56.789Z",
  "job_id": "generation-job-id",
  "event": "candidate_trial",
  "payload": {
    "...": "typed event-specific payload"
  }
}
```

Possible common fields:

```text
sequence
timestamp
job_id
event
payload
```

Optional fields may include:

```text
schema_version
stream_id
```

The agent should avoid adding fields without a clear client-side use.

The outer envelope may internally use a typed union, such as a discriminated union where the `event` field determines the payload type.

Conceptually:

```python
GenerationEvent = (
    ProgressEvent
    | CandidateTrialEvent
    | FloorPlanEvent
    | StatusEvent
    | CompletedEvent
    | ErrorEvent
)
```

The exact Python implementation is left to the agent.

---

# 9. Event Tags and Throttling Groups

Events need a grouping mechanism for throttling.

The original idea referred to this value as a `tag`.

Possible alternative names include:

```text
throttle_group
channel
stream_group
event_group
```

This grouping is mainly an internal delivery concern.

The client may not need to see it if the public event type already provides enough information.

Example internal groups:

```text
candidate_trial
candidate_progress
floor_plan
status
terminal
```

Each group should track throttling independently.

For example, throttling candidate trials should not delay a floor-plan event.

---

# 10. Throttling Behavior

The throttling system should preferably operate per job and per throttle group.

Example configuration:

```text
candidate_trial: 100 ms
progress: 500 ms
floor_plan: no throttle
status: no throttle
terminal: no throttle
```

The exact values should be configurable.

## 10.1 Independent Group Timing

Example:

```text
0 ms   candidate_trial
40 ms  progress
90 ms  candidate_trial
```

If the candidate trial interval is 100 ms:

* the `0 ms` candidate event is sent,
* the `40 ms` progress event may still be sent because it belongs to a different group,
* the `90 ms` candidate event is subject to candidate-trial throttling.

## 10.2 Latest-Event-Wins Behavior

Simply dropping throttled events can leave the client with stale information.

A preferable default for high-frequency state-like events is:

```text
send the first event immediately
retain the latest event received during the throttle window
send the retained latest event when the throttle window expires
```

Example:

```text
0 ms   trial 1
20 ms  trial 2
40 ms  trial 3
60 ms  trial 4
```

With a `100 ms` throttle window:

```text
trial 1 is sent immediately
trial 4 replaces trial 2 and trial 3 as the pending latest event
trial 4 is sent at or after the throttle boundary
```

This avoids sending every intermediate update while still allowing the client to reach the most recent state.

The agent should consider whether this behavior is appropriate for all event types.

For candidate trial visualization, dropping intermediate trials may be acceptable.

For ordered transactional events, coalescing may not be acceptable.

## 10.3 Events That Must Bypass Throttling

Some events should normally be sent immediately:

```text
floor plan available
generation completed
fatal error
cancellation
timeout
```

These may use a priority or bypass flag internally.

A public priority field is not necessarily required.

---

# 11. Backpressure and Queue Limits

A slow or disconnected client should not cause unbounded memory growth.

The implementation should have a clear queue policy.

Possible approaches:

* bounded queue per job,
* coalescing throttled state events,
* replacing older pending events from the same group,
* dropping low-value progress events when the queue is full,
* always preserving terminal events,
* cleaning up queues after disconnect or job completion.

The preferred policy should reflect the fact that:

* candidate trial events are replaceable or droppable,
* progress events are replaceable,
* floor-plan events are valuable,
* terminal events must not be lost.

The agent should inspect how generation jobs and subscribers currently live across processes before choosing an in-memory queue design.

An in-memory queue only works directly when the publisher and SSE consumer share suitable process memory.

If generation runs in a separate worker process, some IPC, shared broker, multiprocessing queue, or existing job-event mechanism may be needed.

This is one of the main areas where repository inspection should override the provisional architecture in this note.

---

# 12. Possible Module Placement

A possible dedicated module is:

```text
app/
└── streaming/
    ├── __init__.py
    ├── api.py
    ├── contracts.py
    ├── models.py
    ├── publisher.py
    ├── dispatcher.py
    ├── throttling.py
    ├── session.py
    ├── config.py
    └── transport/
        ├── __init__.py
        └── sse.py
```

This is only a conceptual proposal.

The project may already have a service or job-management module where some responsibilities fit better.

Possible responsibilities:

## `contracts.py`

Defines public interfaces or protocols such as:

```text
GenerationEventPublisher
GenerationEventSubscriber
```

## `models.py`

Defines typed event envelopes and payloads.

## `publisher.py`

Provides the small API called by the pipeline.

## `dispatcher.py`

Routes published events to the correct job stream or subscribers.

## `throttling.py`

Handles independent throttle groups and latest-event coalescing.

## `session.py`

Represents one generation job's event-stream state.

Possible session data:

```text
job_id
event queue
sequence counter
throttling state
completion state
subscriber state
```

## `config.py`

Defines default throttling and queue behavior.

## `transport/sse.py`

Converts typed events into valid SSE frames and exposes the stream to the FastAPI route.

Some of these files may be unnecessary.

The agent should prefer fewer cohesive modules over creating files merely to match this sketch.

---

# 13. Minimal Pipeline Footprint

The pipeline should interact with one small publisher abstraction.

Possible usage:

```python
progress.candidate_trial(
    trial_number=trial_number,
    candidate_hints=candidate_hints,
)
```

```python
progress.floor_plan(
    floor_plan=floor_plan,
    score=score,
    classification=classification,
)
```

```python
progress.status(
    status=GenerationStatus.USABLE_FLOOR_PLAN_FOUND,
)
```

```python
progress.completed(
    outcome=GenerationOutcome.PRESENTABLE_PLAN_FOUND,
)
```

The algorithms should not manually construct:

* the outer event envelope,
* sequence numbers,
* timestamps,
* job identifiers,
* throttling metadata,
* SSE text,
* or serialized JSON.

Those responsibilities should be handled internally by the publisher and streaming infrastructure.

---

# 14. How the Publisher Reaches Algorithm Code

Several dependency-injection approaches may be feasible.

## Option A: Pipeline Context

Add the publisher to the generation pipeline context:

```text
GenerationContext
    job information
    configuration
    progress publisher
```

Then pipeline-level stages can publish events through the context.

This can be clean if the project already passes a context object through the pipeline.

## Option B: Explicit Optional Parameter

Functions that genuinely publish events accept an optional publisher:

```python
def search_candidates(..., events: GenerationEventPublisher | None = None):
    ...
```

A no-operation implementation can remove repeated `None` checks.

## Option C: Pipeline-Owned Publishing

Keep algorithm modules unaware of streaming.

The pipeline receives normal algorithm results and publishes events around algorithm calls.

This produces the smallest algorithm footprint but may not be sufficient for per-trial candidate events unless candidate search already exposes callbacks, hooks, or yielded results.

## Option D: Event Hook / Observer

Candidate search or other iterative modules may accept a narrowly typed observer interface.

This can work well when streaming updates originate deep inside an iterative algorithm.

The coding agent should select the smallest approach that fits current call paths.

Global mutable publisher state should generally be avoided, especially with concurrent jobs or multiprocessing.

---

# 15. No-Operation Publisher

A no-operation publisher may be useful.

Example concept:

```python
class NullGenerationEventPublisher:
    def candidate_trial(...):
        return None

    def floor_plan(...):
        return None
```

Benefits:

* tests and command-line runners do not require SSE infrastructure,
* generation can run without a connected client,
* algorithm code does not need repeated checks,
* streaming can remain optional.

The agent should determine whether a protocol, abstract base class, or concrete interface best fits the project.

---

# 16. Candidate Search Events

Candidate search is one of the main iterative sources of events.

The requested event content is intentionally small:

```text
trial number
candidate hint points
```

The event should not include:

* full Optuna trial objects,
* complete scoring diagnostics,
* evaluator breakdowns,
* internal trial metadata,
* database objects,
* or unserializable library types.

The agent should determine where the event is best emitted:

* directly after candidate creation,
* after candidate scoring,
* only after a valid candidate result,
* or after the candidate has been normalized into the shared hint model.

If the client is expected to visualize every attempted candidate, the event may be emitted before eligibility filtering.

If the client is expected to visualize only meaningful candidate results, it may be emitted after validation or scoring.

This behavior should be decided from existing client expectations and pipeline semantics.

---

# 17. Floor-Plan Events

A floor-plan event should be emitted only when the plan is useful to the client.

The desired plan includes openings.

Therefore, the event should likely be emitted after:

```text
solver
post-processing
opening generation
validation
scoring
```

or at whichever active stage produces the final client-facing floor-plan representation.

The coding agent should inspect the actual stage order because older documentation may not match the active execution path.

Avoid emitting raw solver geometry if the client expects the post-processed plan with doors and windows.

Possible emission rules:

* emit when a usable floor plan is found,
* emit when a presentable floor plan is found,
* emit a final selected plan when the job ends,
* avoid re-emitting identical plan data unnecessarily.

If plans are large, the agent should consider:

* serialization cost,
* network cost,
* whether unchanged metadata can be omitted,
* and whether duplicate plan events should be deduplicated.

However, premature delta-based floor-plan protocols are probably unnecessary unless payload size becomes a measured problem.

---

# 18. Status and Message Handling

Status information should be machine-readable where possible.

Prefer:

```json
{
  "status": "presentable_floor_plan_found"
}
```

over:

```json
{
  "message": "Great news! A presentable floor plan was found."
}
```

The frontend can map status codes to localized or user-friendly text.

A short optional message may still be included for errors or compatibility, but it should not become the main API contract.

Potential status codes:

```text
job_started
candidate_search_started
floor_plan_generation_started
usable_floor_plan_found
presentable_floor_plan_found
timeout_reached
job_completed
job_cancelled
```

Only statuses that the frontend needs should be included.

---

# 19. SSE Transport Behavior

The transport layer should convert the typed event model into valid SSE frames.

Conceptually:

```text
event: candidate_trial
id: 152
data: {...serialized event...}
```

The agent should determine whether the frontend will consume:

* the native SSE `event` field,
* the JSON envelope's `event` field,
* or both.

Using both may be useful but should remain consistent.

The implementation should also consider:

* heartbeat or keep-alive comments,
* proxy buffering,
* disconnected clients,
* graceful generator cancellation,
* cleanup after job completion,
* correct content type,
* cache-control headers,
* and reverse-proxy configuration.

These are transport concerns and should not affect algorithm modules.

---

# 20. Reconnection and Event IDs

The common `sequence` value may also be used as the SSE event ID.

This can support ordering and future reconnection behavior.

However, full replay support should only be implemented if required.

If the server does not retain event history, the presence of `Last-Event-ID` should not falsely imply guaranteed replay.

A pragmatic first version may provide:

* monotonically increasing sequence numbers,
* event ordering,
* but no historical replay.

The agent should document the actual behavior.

---

# 21. Multiple Subscribers

The agent should inspect whether a generation job may have:

* exactly one client stream,
* multiple browser tabs,
* multiple subscribers,
* reconnecting subscribers,
* or administrative observers.

A single queue consumed by multiple clients will distribute events rather than broadcast them.

If multiple subscribers are supported, the implementation may require:

* one queue per subscriber,
* a broadcast dispatcher,
* or an existing pub/sub mechanism.

This design decision should come from the active product behavior rather than assumptions in this note.

---

# 22. Lifecycle and Cleanup

Each generation event stream should have a defined lifecycle.

Possible states:

```text
created
running
completed
failed
cancelled
expired
```

Cleanup should occur when:

* the generation finishes,
* a fatal error occurs,
* the job is cancelled,
* the stream is no longer needed,
* or a configured retention period expires.

The implementation should avoid leaving:

* abandoned queues,
* throttle timers,
* subscriber references,
* job sessions,
* or pending tasks.

The agent should integrate cleanup with the existing generation job lifecycle rather than introducing a separate conflicting lifecycle.

---

# 23. Configuration

Possible configuration values:

```text
candidate_trial_throttle_ms
progress_throttle_ms
queue_capacity
heartbeat_interval_seconds
completed_session_retention_seconds
```

Configuration may be:

* global,
* profile-specific,
* job-specific,
* or partially hardcoded where configurability adds no value.

Not every theoretical setting needs to become a public configuration option.

A reasonable default policy might be:

```text
candidate trial: throttled
progress: throttled
floor plan: immediate
status: immediate
completed: immediate
error: immediate
```

The exact defaults should be determined by real event frequency and frontend rendering cost.

---

# 24. Testing Expectations

The coding agent should create tests appropriate to the final architecture.

Important behaviors to verify include:

## Typed Contracts

* valid payloads serialize correctly,
* invalid payloads are rejected,
* event type and payload type cannot be mismatched,
* canonical floor-plan and hint types are converted correctly.

## Throttling

* throttling is independent per group,
* the first event can be sent immediately,
* latest-event-wins behavior works,
* high-priority or bypass events are immediate,
* pending events are cleaned up after completion.

## Queue Behavior

* queue limits are respected,
* low-value events can be dropped or replaced safely,
* floor-plan and terminal events are preserved,
* disconnected subscribers do not leak resources.

## Ordering

* sequence numbers increase correctly,
* terminal events are emitted after earlier accepted events,
* no normal events are emitted after stream completion.

## Transport

* SSE formatting is valid,
* event IDs are correct,
* JSON payloads are valid,
* heartbeat behavior works,
* client disconnection is handled.

## Pipeline Integration

* generation works with the real publisher,
* generation also works with the null publisher,
* candidate trial events are emitted from the intended point,
* floor-plan events contain openings,
* no detailed scoring diagnosis is exposed.

---

# 25. Logging

SSE delivery and internal logging should remain separate.

Publishing an event may also create a structured log where useful, but client events should not simply be generated from arbitrary logs.

Important server-side logging may include:

```text
subscriber connected
subscriber disconnected
event queue overflow
event serialization failure
event delivery failure
job stream completed
stream cleanup performed
```

Floor-plan generation diagnostics should continue using the existing logging system.

---

# 26. Security and Data Exposure

Before sending any model through SSE, verify that it does not expose:

* internal exception details,
* filesystem paths,
* database implementation fields,
* private user information,
* internal profile configuration,
* development diagnostics,
* or unserializable Python objects.

The floor-plan payload should match the intended client-facing response contract as closely as practical.

Error messages should use stable client-safe codes.

---

# 27. Suggested Scope for the First Version

A pragmatic first version could support:

```text
candidate_trial
progress
floor_plan
status
completed
error
```

with:

* strongly typed payloads,
* one consistent envelope,
* one event publisher interface,
* per-job streaming,
* per-group throttling,
* latest-event-wins for replaceable events,
* immediate terminal and floor-plan delivery,
* bounded queues,
* cleanup,
* and basic keep-alive behavior.

Features that may be deferred unless already required:

* durable event replay,
* cross-instance pub/sub,
* WebSocket support,
* historical stream persistence,
* complex priority scheduling,
* payload delta compression,
* multiple stream schema versions,
* detailed client diagnostics.

---

# 28. Decisions the Coding Agent Should Make After Inspection

The coding agent should explicitly determine:

1. Where generation currently runs relative to the FastAPI process.
2. Whether an in-memory queue is viable.
3. Whether existing job infrastructure already has event storage or pub/sub behavior.
4. Whether multiple SSE subscribers must be supported.
5. Where candidate trial callbacks can be added with the least coupling.
6. At which exact stage a floor plan has final openings and client-ready geometry.
7. Which canonical models can be reused directly.
8. Which models require dedicated transport schemas.
9. Whether the generation route already returns or streams job results.
10. How cancellation and client disconnection should interact with generation.
11. What terminal result currently ends the pipeline.
12. What event frequency is realistic during candidate search.
13. Whether floor-plan payload size requires deduplication.
14. Which proposed files and abstractions are unnecessary.
15. Whether the term `progress`, `publisher`, `session`, `channel`, or `throttle_group` conflicts with existing project terminology.

The implementation plan should be based on these findings.

---

# 29. Desired Final Characteristics

The final solution should aim for the following characteristics:

* The pipeline makes small, readable event-publishing calls.
* Algorithm modules do not depend on FastAPI or SSE.
* Event payloads are strongly typed.
* The client receives only useful product-level information.
* High-frequency events are throttled independently.
* The latest relevant state is not permanently lost due to throttling.
* Floor plans and terminal events are delivered immediately.
* Queue growth is bounded.
* Multiple concurrent jobs do not share event state.
* Stream resources are cleaned up reliably.
* The generation pipeline can run without an SSE client.
* Existing command-line runners and tests can use a no-operation publisher.
* The design follows active project architecture rather than older unused code.

---

# 30. Requested Agent Workflow

Please treat this document as a detailed proposal rather than a direct instruction set.

Recommended workflow:

1. Inspect the active repository and identify the real generation and job execution paths.
2. Compare the proposal with the current architecture.
3. Point out any assumptions here that do not fit the project.
4. Produce an implementation plan based on repository findings.
5. Revise names, layers, file locations, and contracts where appropriate.
6. Keep the pipeline and algorithms minimally coupled to the streaming transport.
7. Implement only after the final design has been grounded in the active codebase.

The goal is not to reproduce this proposal exactly.

The goal is to implement a maintainable, strongly typed, low-footprint event-streaming feature that fits the actual project.

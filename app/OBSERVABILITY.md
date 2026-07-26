# FPG observability

Every active generation invocation receives one immutable `ExecutionContext`.
Its `flow_id` identifies the internal execution; `job_id` remains separate
external metadata. Optuna's zero-based number is the `search_trial_id`.
Eligible candidates receive one-based, flow-local `candidate_id` values, and
each CP-SAT execution receives a one-based `solver_run_id` scoped to its
candidate.

The generation entry point reserves `output/flows/<timestamp>_flow`. Concurrent
collisions receive `-02`, `-03`, and later suffixes. A flow directory contains
only `json/` and `png/`. JSON event records live under
`json/logs/<feature>/`; detailed JSON and PNG artifacts live in their
feature-owned format directory.

Algorithm features own event names and domain serialization in their local
`logging/` package. Normal feature modules must not import `app.util.logger` or
`app.artifacts`. Feature logging packages may use the shared base logger and
artifact storage, but may not import another feature logger.

To add an event:

1. Add a typed value to the feature's `logging/events.py`.
2. Add or reuse a meaningful wrapper in `logging/logger.py`.
3. Emit the event at the feature API or manager boundary with its
   `ExecutionContext`.

To save detailed JSON, create a structured `ArtifactWriteRequest` in the
feature logging package and call `ArtifactStorage.save_json`. To save a PNG,
render the figure through visualization; its output manager encodes the figure
and delegates persistence to `ArtifactStorage.save_png`. Callers never construct
output paths.

Application events use `output/application/json/<date>/`. Logging failures are
reported to stderr and never fail floor-plan generation.

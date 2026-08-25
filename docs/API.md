# Floor Plan Generator API v1

This is the complete frontend integration contract for `fpg-server`.

## 1. Base contract

- Default base URL: `http://localhost:8000`
- API prefix: `/api/v1`
- REST request and response media type: `application/json`
- Event stream media type: `text/event-stream`
- OpenAPI: `/openapi.json`
- Interactive schema browser: `/docs`
- Unknown JSON fields are rejected.
- Boolean values are never accepted as integers.
- All dimensions and coordinates are integer project units: **10 units = 1 meter** and **1 unit = 10 cm**.
- Area values are square project units. Divide by `100` to obtain square meters.
- Front is negative Y (`-Y`), back is `+Y`, left is `-X`, and right is `+X`.
- Room-type strings are exact, lowercase enum values. The server does not normalize aliases, spaces, hyphens, or case.
- BLSP and FPG are independent. A floor-plan job never requires a BLSP flow ID.

### Common enums

Room types:

```text
bedroom
bathroom
attached_bathroom
living_room
kitchen
dining_room
hallway
veranda
garage
```

Road roles: `main_entry`.

Road types: `main_road`, `private_road`.

Usable-land alignments: `parallel_to_entry_road`, `perpendicular_to_entry_road`.

Job states:

```text
queued
running
cancellation_requested
completed
failed
cancelled
timed_out
```

`completed`, `failed`, `cancelled`, and `timed_out` are terminal.

### Common error envelope

Every non-success JSON response uses:

```json
{
  "error": {
    "code": "invalid_request",
    "message": "The request is invalid.",
    "stage": "request_validation",
    "details": {
      "errors": [
        {
          "location": ["body", "floor_limits", "max_width"],
          "code": "int_type",
          "message": "Input should be a valid integer"
        }
      ]
    }
  }
}
```

The frontend must branch on `error.code`, not `message`. `message` is displayable English text. `details` is always an object but its fields depend on the code.

Common HTTP codes:

| HTTP | Code | Meaning |
|---|---|---|
| 404 | `not_found` | Unknown non-job route. |
| 404 | `job_not_found` | Job is unknown or its API retention period expired. |
| 409 | `job_not_cancellable` | Job is already terminal. |
| 422 | `invalid_request` | JSON shape, enum, integer, or field validation failed. |
| 429 | `queue_full` | Running and queued generation capacities are full. |
| 500 | `reference_data_unavailable` | Valid server configuration is unavailable. |
| 500 | `unexpected_error` | Unhandled API failure. |

## 2. Metadata

### `GET /api/v1/metadata`

Use this endpoint to build room, road, size, and aspect-ratio selectors. Do not hardcode configurable limits.

Success: `200 OK`

```json
{
  "schema_version": 2,
  "project_units_per_meter": 10,
  "front_axis": "-Y",
  "road_types": [
    {"value": "main_road", "name": "MAIN_ROAD", "display_name": "Main Road"},
    {"value": "private_road", "name": "PRIVATE_ROAD", "display_name": "Private Road"}
  ],
  "room_requirements": [
    {
      "room_type": "bedroom",
      "min_count": 1,
      "max_count": 4,
      "client_selectable": true
    },
    {
      "room_type": "hallway",
      "min_count": 1,
      "max_count": 1,
      "client_selectable": false
    }
  ],
  "room_sizes": [
    {
      "room_type": "bedroom",
      "size": "regular",
      "min_width": 30.0,
      "max_width": 42.0,
      "min_area": 900.0,
      "max_area": 1764.0
    }
  ],
  "compatible_aspect_ratios": [
    {"label": "1:1", "value": 1.0}
  ]
}
```

`room_requirements` includes server-created types such as `hallway`. Never include a room with `client_selectable: false` in a generation request.

Failures: `500 reference_data_unavailable`.

## 3. Buildable land space

### `POST /api/v1/buildable-space`

This synchronous endpoint validates one convex parcel, applies the configured setbacks, and finds the largest supported rectangular usable floor envelope.

Request:

```json
{
  "land_boundary": {
    "points": [
      {"x": 0, "y": 0},
      {"x": 200, "y": 0},
      {"x": 200, "y": 160},
      {"x": 0, "y": 160}
    ]
  },
  "roads": [
    {
      "boundary_edge_index": 0,
      "role": "main_entry",
      "road_type": "main_road"
    }
  ]
}
```

Rules:

- Supply at least four ordered boundary points. A repeated closing point is allowed by the geometry package but is unnecessary.
- Coordinates must be integers.
- The effective polygon must be unique, finite, non-collinear, non-self-intersecting, positive-area, and convex.
- Exactly one supported main-entry road is currently required.
- `boundary_edge_index` is zero-based and refers to the input edge from point `i` to point `(i + 1) mod point_count`.

Success: `200 OK`. Header `X-Flow-ID` equals body `flow_id`.

```json
{
  "flow_id": "21c59ae1-9e79-4ff0-b378-358353f56d98",
  "units": {"project_units_per_meter": 10},
  "original_land": {"area": 32000.0},
  "buildable_land": {
    "boundary": {
      "points": [
        {"x": 15.0, "y": 10.0},
        {"x": 190.0, "y": 10.0},
        {"x": 190.0, "y": 130.0},
        {"x": 15.0, "y": 130.0}
      ]
    },
    "area": 21000.0,
    "edge_setbacks": [
      {
        "edge_index": 0,
        "side": "front",
        "base_setback": 10,
        "road_adjustment": 5,
        "final_setback": 15,
        "road_type": "main_road"
      }
    ]
  },
  "usable_land": {
    "boundary": {
      "points": [
        {"x": 15.0, "y": 10.0},
        {"x": 190.0, "y": 10.0},
        {"x": 190.0, "y": 130.0},
        {"x": 15.0, "y": 130.0}
      ]
    },
    "width": 175,
    "length": 120,
    "area": 21000,
    "floor_width_alignment": "parallel_to_entry_road",
    "entry_road_edge_index": 0
  },
  "reference_profile": "mock_residential_v1"
}
```

The coordinates above are illustrative; the server-calculated values are authoritative.

Business validation returns `422` with one of:

```text
invalid_request
invalid_land_boundary
non_convex_land
self_intersecting_land
invalid_road_attachment
multiple_main_entry_roads
unsupported_road_type
setback_eliminates_buildable_land
no_usable_land_found
search_limit_exceeded
usable_land_calculation_failed
buildable_land_calculation_failed
```

Configuration/unexpected failures return `500` with `reference_data_error` or `unexpected_buildable_space_error`.

## 4. Floor-plan jobs

### 4.1 Create a job

### `POST /api/v1/floor-plan-jobs`

Request:

```json
{
  "floor_limits": {
    "max_width": 120,
    "max_length": 100
  },
  "aspect_ratio": "4:3",
  "rooms": [
    {"room_type": "bedroom", "id": "bedroom-1", "name": "Bedroom 1", "requested_size": "regular"},
    {"room_type": "bedroom", "id": "bedroom-2", "name": "Bedroom 2", "requested_size": "regular"},
    {"room_type": "bathroom", "id": "bathroom-1", "requested_size": "regular"},
    {"room_type": "living_room", "id": "living-1", "requested_size": "regular"},
    {"room_type": "kitchen", "id": "kitchen-1", "requested_size": "regular"},
    {"room_type": "dining_room", "id": "dining-1", "requested_size": "regular"},
    {"room_type": "veranda", "id": "veranda-1", "requested_size": "regular"}
  ]
}
```

Rules:

- `max_width` and `max_length` are required positive integers in project units.
- `aspect_ratio` accepts a positive number, numeric string, ratio string, or configured metadata label.
- `rooms` must contain at least one client-selectable room. Preprocessing adds/validates configured mandatory rooms.
- `id`, `name`, and `requested_size` may be omitted or `null`; preprocessing supplies configured defaults. Explicit IDs must become unique.
- Never submit `hallway`; the server controls hallway candidates.

Generation behavior relevant to clients:

- Candidate circulation removes unused hallway hints and may consolidate nearby redundant hallway hints before solving. The final hallway count can therefore be lower than the preprocessing/search maximum.
- Opening generation requires one main entrance and a connected selected-door path from that entrance to every configured required-access room. A layout that cannot satisfy this is rejected as a recoverable generation attempt rather than returned as a completed plan.
- Solver profiles penalize excessive hallway area and hallway length as a soft objective. This changes layout preference, not the floor-plan response schema.

Success: `202 Accepted`

```json
{
  "job_id": "064b322c-78f6-4433-887a-21d78897935c",
  "state": "queued",
  "status_url": "/api/v1/floor-plan-jobs/064b322c-78f6-4433-887a-21d78897935c",
  "events_url": "/api/v1/floor-plan-jobs/064b322c-78f6-4433-887a-21d78897935c/events",
  "cancellation_url": "/api/v1/floor-plan-jobs/064b322c-78f6-4433-887a-21d78897935c"
}
```

Open `events_url` immediately. Creation and execution are independent from the SSE connection, so a disconnected client does not cancel a job.

Failures: `422 invalid_request`, `429 queue_full`, `500 unexpected_error`.

### 4.2 Read status/result

### `GET /api/v1/floor-plan-jobs/{job_id}`

Success: `200 OK`

```json
{
  "job_id": "064b322c-78f6-4433-887a-21d78897935c",
  "state": "completed",
  "created_at": "2026-08-14T08:30:00.000000+00:00",
  "started_at": "2026-08-14T08:30:00.050000+00:00",
  "completed_at": "2026-08-14T08:30:42.100000+00:00",
  "result": {
    "floor_plan": {},
    "scoring": {
      "total_score": 92.5,
      "passed_critical": true,
      "critical_failure": null
    },
    "classification": "presentable",
    "outcome": "presentable_plan_found"
  },
  "error": null
}
```

Before terminal completion, `completed_at`, `result`, and `error` are `null`. A `failed` or `cancelled` job has `result: null` and a structured `error`. A `timed_out` job can include a `best_available` result and still has state `timed_out`; never treat it as normal completion.

Completed classifications: `presentable`, `usable`. Outcomes: `presentable_plan_found`, `best_usable_plan_returned`.

Jobs remain accessible for 3600 seconds by default after becoming terminal. Artifacts remain on the server after API retention expires. After expiry this endpoint returns `404 job_not_found`.

### 4.3 Cancel

### `DELETE /api/v1/floor-plan-jobs/{job_id}`

New request: `202 Accepted`

```json
{
  "job_id": "064b322c-78f6-4433-887a-21d78897935c",
  "status": "cancellation_requested"
}
```

Repeated request while cancellation is pending: `200 OK`, status `already_requested`.

Queued jobs become `cancelled` immediately. Running jobs are signalled cooperatively and forcibly terminated after the configured grace period if necessary. A cancellation request racing with natural completion may receive `409 job_not_cancellable`; fetch the status endpoint for the authoritative terminal result.

Failures: `404 job_not_found`, `409 job_not_cancellable`.

## 5. SSE events

### `GET /api/v1/floor-plan-jobs/{job_id}/events`

Open with the browser's native `EventSource`. Success headers include:

```text
Content-Type: text/event-stream
Cache-Control: no-cache, no-transform
X-Accel-Buffering: no
X-Generation-Job-ID: <job_id>
```

Unknown/expired jobs return a normal JSON `404 job_not_found` response before streaming starts.

### Wire format

```text
id: 12
event: candidate
data: {"schema_version":"1.0","job_id":"...","sequence":12,...}

```

The SSE `event` field is one of `job`, `stage`, `candidate`, `floor_plan`, `attempt_error`, or `terminal`. The `id` equals `data.sequence`.

Every JSON envelope has:

```json
{
  "schema_version": "1.0",
  "job_id": "064b322c-78f6-4433-887a-21d78897935c",
  "sequence": 12,
  "event_type": "candidate",
  "stage": "candidate_scoring",
  "state": "accepted",
  "message": "Candidate scored",
  "data": {},
  "error": null,
  "trial_number": 8,
  "candidate_id": null,
  "timestamp_utc": "2026-08-14T08:30:05.000000+00:00"
}
```

`sequence` is strictly increasing within a job. Timestamps are UTC ISO 8601. Non-applicable trial/candidate IDs are `null`.

### Event catalog

| Event | Stage/state | Important `data` |
|---|---|---|
| `job` | `job/queued` | Empty. |
| `job` | `job/running` | `timeout_seconds`. |
| `job` | `job/cancellation_requested` | Empty. |
| `stage` | `preprocessing/started` | Empty; show “Preprocessing”. |
| `stage` | `preprocessing/completed` | `floor_width`, `floor_length`. |
| `stage` | `candidate_search/started` | `trial_limit`. |
| `candidate` | `candidate_search/generated` | `candidate_hints`. |
| `stage` | `candidate_circulation/started` | Show “Filtering Hint Map”. |
| `candidate` | `candidate_scoring/accepted|rejected` | `score`, `threshold`, `accepted`, `circulation_artifact`. |
| `stage` | `initial_generation/started` | Show “Generating Floor Plan”. |
| `floor_plan` | `initial_generation/completed` | `floor_plan`. |
| `stage` | `refinement_a|refinement_b/started` | Show active refinement label. |
| `floor_plan` | `refinement_a|refinement_b/completed` | Refined `floor_plan`. |
| `stage` | `post_processing/started` | Show “Post Processing”. |
| `stage` | `openings/started` | Show “Generating Openings”. |
| `stage` | `final_scoring/started` | Show “Final Scoring”. |
| `floor_plan` | `final_scoring/completed` | `floor_plan`, `score`, `passed_critical`. |
| `attempt_error` | failing stage/`failed` | Structured recoverable `error`; continue listening. |
| `terminal` | `job/completed|failed|cancelled|timed_out` | Completed/best result when available plus nonrecoverable `error` on adverse outcomes. |

Candidate hints:

```json
[
  {
    "room_id": "bedroom-1",
    "x": 20.0,
    "y": -10.0,
    "room_type": "bedroom",
    "hint_index": 1
  }
]
```

Candidate-circulation path nodes are deliberately not transmitted. `circulation_artifact` is an output-relative server artifact reference such as `flows/<flow>/json/candidate_circulation/trial-000008.json`.

Recoverable error:

```json
{
  "code": "solver_infeasible",
  "message": "The solver did not find a feasible layout.",
  "recoverable": true,
  "details": {"solver_status": "infeasible"}
}
```

Do not close or mark the UI failed for `attempt_error`. Only `terminal` ends the job.

### Replay and reconnection

- Every logical event is persisted before publication.
- A first connection replays all existing events starting at sequence 1.
- Browser `EventSource` automatically sends `Last-Event-ID` when reconnecting. The server resumes at the next sequence.
- A manual client may set `Last-Event-ID: 12`; it must be a non-negative integer.
- If there is no logical event for the configured interval, the server sends `: heartbeat`. Heartbeats contain no JSON, have no ID, and must not update UI state.
- After replaying the terminal event, the server closes the stream.
- Multiple subscribers may observe the same job. Replay can cause the same logical event to be delivered again if a client did not durably record its ID; deduplicate by `sequence`.

Browser example:

```js
const created = await fetch(`${baseUrl}/api/v1/floor-plan-jobs`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(requestBody),
}).then(async (response) => {
  const body = await response.json();
  if (!response.ok) throw body.error;
  return body;
});

const source = new EventSource(`${baseUrl}${created.events_url}`);

for (const type of ["job", "stage", "candidate", "floor_plan", "attempt_error", "terminal"]) {
  source.addEventListener(type, (message) => {
    const event = JSON.parse(message.data);
    if (event.sequence <= lastAppliedSequence) return;
    lastAppliedSequence = event.sequence;
    applyGenerationEvent(event);
    if (event.event_type === "terminal") source.close();
  });
}

source.onerror = () => {
  // Do not mark the job failed. EventSource reconnects automatically.
  // If retries are exhausted by application policy, fetch created.status_url.
};
```

## 6. Floor-plan and scoring schemas

Every `floor_plan` object is:

```json
{
  "boundary": {
    "points": [{"x": 0.0, "y": 0.0}]
  },
  "rooms": [
    {
      "id": "bedroom-1",
      "room_type": "bedroom",
      "name": "Bedroom 1",
      "boundary": {"points": [{"x": 0.0, "y": 0.0}]},
      "role": "standard",
      "parent_room_id": null,
      "metadata": {
        "source_room_ids": ["bedroom-1"],
        "applied_transformations": []
      }
    }
  ],
  "openings": [
    {
      "id": "opening-1",
      "opening_type": "door",
      "purpose": "room_connection",
      "start": {"x": 10.0, "y": 20.0},
      "end": {"x": 18.0, "y": 20.0},
      "connected_room_ids": ["bedroom-1", "hallway-1"]
    }
  ],
  "identity_redirects": {},
  "applied_transformations": []
}
```

Opening types: `door`, `window`.

Opening purposes: `room_connection`, `main_entrance`, `secondary_entrance`, `daylight`.

For a successfully generated non-empty terminal plan, the opening solver selects exactly one `main_entrance` and enforces door-network access for configured required room types. Interior door compatibility is explicit; unsupported room-type pairs are not connected implicitly. Door placement prefers usable wall ends/corners according to server room-type priority, while windows remain center-oriented.

Room roles: `standard`, `solver_placeholder`. Terminal plans should not contain solver placeholders; intermediate plans may.

Terminal `scoring` is:

```json
{
  "total_score": 92.5,
  "passed_critical": true,
  "critical_failure": null
}
```

If non-null, `critical_failure` contains a stable finding `code`, displayable `message`, `severity`, affected `subject_ids`, and numeric `metrics`.

Current final scoring uses two groups:

- `critical`: geometry integrity, required adjacency, enclosed voids, and inward recess. Each enabled critical evaluator must score `100` to pass the gate.
- `functional`: room-size consistency (weight `2`) and kitchen/dining proximity (weight `1`). Room-size consistency evaluates configured cross-room-type area ratios and bedroom area spread, while accounting for size ranges that are impossible to satisfy exactly for the current generation specification.

The functional scoring model changed from earlier server versions that used living-room-balance and bedroom-quality evaluators, so `total_score` values should not be compared directly across those versions.

## 7. Frontend state machine

Recommended reducer behavior:

```text
create request
  -> 202 queued
  -> connect EventSource

queued
  -> running
  -> cancelled

running
  -> apply stage/candidate/floor_plan events in sequence order
  -> keep latest intermediate floor plan for visualization
  -> show attempt_error as a recoverable warning
  -> cancellation_requested
  -> completed | failed | cancelled | timed_out

cancellation_requested
  -> completed (natural completion won the race)
  -> cancelled
  -> timed_out

terminal
  -> close EventSource
  -> persist terminal payload
  -> optionally GET status_url to confirm/recover the retained result
```

Rendering rules:

- `queued`: show queue state and enable cancel.
- `running`: show `message`, trial progress, candidate hints, and latest floor plan.
- `attempt_error`: show a non-blocking warning and continue.
- `completed`: render `result.floor_plan`; label by `classification`.
- `timed_out`: clearly label timeout. If a `best_available` result exists, offer it as incomplete/best-effort output.
- `failed`: show terminal `error.message`; preserve `error.code` for support/analytics.
- `cancelled`: show cancellation and discard incomplete visual state unless product design chooses to retain it locally.
- `404 job_not_found` during recovery: the server retention window expired; local persisted frontend data is the only remaining client copy.

## 8. Operational behavior relevant to clients

- Default capacity is one running job plus sixteen queued jobs.
- The 60-second default deadline starts when a job enters `running`, not while it waits in `queued`.
- Server restart does not resume active computation. Retained active snapshots become `failed` with code `server_restarted`; already-terminal retained results remain readable.
- Disconnecting SSE never terminates a job. Use `DELETE` explicitly.
- API request/response JSON is logged with credential-like fields redacted. SSE logical events are logged once in the job journal rather than duplicated for each network replay.
- Runtime path/log artifact references are for diagnostics and are not public download endpoints unless a separate authenticated artifact API is introduced later.

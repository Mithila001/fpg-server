# Floor Plan Generation API

Client integration contract for the floor-plan generation endpoints.

## 1. Scope

This document covers only:

- `POST /generation` — wait for one JSON result.
- `POST /generation/stream` — receive generation updates and a floor plan through Server-Sent Events (SSE).

Both endpoints accept the same JSON request.

The API currently has no endpoint authentication. The deployment's base URL is environment-specific. In the default Docker Compose setup, the base URL is `http://127.0.0.1:8001`; a directly launched Uvicorn server normally uses `http://127.0.0.1:8000`.

## 2. Units and coordinate system

All request dimensions, response coordinates, lengths, and areas use project units:

```text
10 project units = 1 meter
1 project unit = 0.1 meter = 10 centimeters
```

The floor-plan coordinate system is:

```text
                 Back (+Y)
                     ↑
                     |
Left (-X)  ←---------+---------→  Right (+X)
                     |
                     ↓
                 Front (-Y)
```

The front of the generated house faces negative Y. Polygon boundaries are represented by ordered points. Clients must draw the closing edge from the last point back to the first point; the first point is not required to be repeated at the end.

## 3. Common request contract

### 3.1 Headers

For both endpoints:

```http
Content-Type: application/json
```

For the streaming endpoint, also send:

```http
Accept: text/event-stream
```

### 3.2 TypeScript definition

```ts
type RoomType =
  | "bedroom"
  | "bathroom"
  | "attached_bathroom"
  | "living_room"
  | "kitchen"
  | "dining_room"
  | "hallway"
  | "veranda"
  | "garage"
  | "open_area";

interface GenerationRequest {
  floor_limits: {
    max_width: number;  // Required; finite and > 0.
    max_length: number; // Required; finite and > 0.
  };
  aspect_ratio: number | string;
  rooms: GenerationRoomRequest[]; // Required; at least one item.
}

interface GenerationRoomRequest {
  room_type: RoomType;       // Required; exact, case-sensitive enum value.
  id?: string | null;        // Optional; generated when omitted, null, or blank.
  name?: string | null;      // Optional; generated when omitted, null, or blank.
  requested_size?: string | null; // Optional; default is "regular".
  required?: boolean;        // Optional; default is true.
}
```

### 3.3 Field rules

| JSON path | Required | Accepted value | Rules |
|---|---:|---|---|
| `floor_limits` | Yes | object | Must contain `max_width` and `max_length`. Unknown properties inside this object are rejected. |
| `floor_limits.max_width` | Yes | number | Must be finite and greater than `0`. |
| `floor_limits.max_length` | Yes | number | Must be finite and greater than `0`. |
| `aspect_ratio` | Yes | number or string | Numeric value must be finite, positive, and between `0.5` and `2.0`, inclusive. A string must use `H:W`, such as `"4:3"`; it is converted to `H / W` and must satisfy the same range. |
| `rooms` | Yes | array | Must contain at least one room. |
| `rooms[].room_type` | Yes | `RoomType` | Exact lowercase enum value only. Aliases such as `"Garage"`, `"livingRoom"`, and `"garage-room"` are invalid. |
| `rooms[].id` | No | string or null | Leading/trailing whitespace is removed. A missing, null, or blank ID is generated as `<room_type>_<number>`. Final IDs must be non-empty and unique. Treat IDs as opaque, case-sensitive strings. |
| `rooms[].name` | No | string or null | Leading/trailing whitespace is removed. If missing, null, or blank, a display name is generated from the ID. |
| `rooms[].requested_size` | No | non-empty string or null | Defaults to `"regular"`. Values are trimmed, lowercased, and spaces/hyphens become underscores. The current reference profile defines only `"regular"`; clients should send `"regular"` or omit this field. |
| `rooms[].required` | No | boolean | Defaults to `true`. Some policy-required and derived room types are always treated as required. |

JSON `null` is not accepted for `floor_limits`, `aspect_ratio`, `rooms`, `room_type`, or `required`.

Top-level unknown properties and unknown properties inside `rooms[]` are currently ignored. Clients should not depend on that behavior; only send documented properties. Unknown properties inside `floor_limits` are rejected.

### 3.4 Generation policy visible to clients

The current generation profile requires at least one of each:

- `bedroom`
- `bathroom`
- `kitchen`
- `veranda`

The service derives one `living_room` when none is supplied and derives hallways when needed. At most one `living_room` may be supplied.

Each `attached_bathroom` requires a distinct `bedroom`; the number of attached bathrooms cannot exceed the number of bedrooms.

Optional room types may still make a request impossible when the requested maximum floor is too small.

### 3.5 Valid request example

```json
{
  "floor_limits": {
    "max_width": 120,
    "max_length": 100
  },
  "aspect_ratio": "4:3",
  "rooms": [
    {
      "id": "bedroom_1",
      "room_type": "bedroom",
      "name": "Bedroom 1",
      "requested_size": "regular",
      "required": true
    },
    {
      "id": "bathroom_1",
      "room_type": "bathroom",
      "requested_size": "regular"
    },
    {
      "id": "kitchen_1",
      "room_type": "kitchen",
      "requested_size": "regular"
    },
    {
      "id": "veranda_1",
      "room_type": "veranda",
      "requested_size": "regular"
    }
  ]
}
```

## 4. Shared floor-plan response types

The following types are used by the synchronous success response and by SSE `floor_plan` events.

```ts
interface Point {
  x: number;
  y: number;
}

interface Polygon {
  points: Point[];
}

type RoomRole = "standard" | "solver_placeholder";

interface RoomMetadata {
  source_room_ids: string[];
  applied_transformations: string[];
}

interface FloorPlanRoom {
  id: string;
  room_type: RoomType;
  name: string;
  boundary: Polygon;
  role: RoomRole;
  parent_room_id: string | null;
  metadata: RoomMetadata;
}

type OpeningType = "door" | "window";

type OpeningPurpose =
  | "room_connection"
  | "main_entrance"
  | "secondary_entrance"
  | "daylight";

interface FloorPlanOpening {
  id: string;
  opening_type: OpeningType;
  purpose: OpeningPurpose;
  start: Point;
  end: Point;
  connected_room_ids: string[];
}

interface FloorPlan {
  boundary: Polygon;
  rooms: FloorPlanRoom[];
  openings: FloorPlanOpening[];
  identity_redirects: Record<string, string>;
  applied_transformations: string[];
}
```

Field semantics:

| Field | Meaning |
|---|---|
| `floor_plan.boundary` | Outer generated floor boundary. |
| `rooms[].boundary` | Ordered polygon vertices for that room. |
| `rooms[].id` | Canonical room identifier used by openings and scoring findings. |
| `rooms[].parent_room_id` | Parent room ID when the room was derived from another room; otherwise `null`. |
| `rooms[].metadata.source_room_ids` | Source room IDs retained after transformations or merges. |
| `rooms[].metadata.applied_transformations` | Transformations applied specifically to the room. |
| `openings[].start`, `openings[].end` | Endpoints of the door or window segment. |
| `openings[].connected_room_ids` | Rooms connected by the opening. An exterior opening may have only one connected room. |
| `identity_redirects` | Map from a replaced/merged room ID to its surviving canonical room ID. Resolve IDs through this map when retaining references to earlier room identities. |
| `applied_transformations` | Transformations applied to the plan as a whole. |

All fields shown above are present in a serialized `FloorPlan`, including arrays and objects that happen to be empty.

## 5. Synchronous endpoint

### 5.1 Request

```http
POST /generation
Content-Type: application/json
Accept: application/json
```

The request body is `GenerationRequest`.

The call remains open until generation succeeds or fails. The configured generation search timeout is approximately 60 seconds, but request processing and network overhead can make the HTTP request last longer. Client, gateway, and reverse-proxy timeouts must exceed the server's generation duration.

### 5.2 Success response

```http
HTTP/1.1 200 OK
Content-Type: application/json
```

```ts
interface GenerationResponse {
  floor_plan: FloorPlan;
  scoring: FloorPlanScoring;
}
```

### 5.3 Scoring contract

```ts
type EvaluationStatus = "completed" | "not_applicable" | "skipped";
type GroupStatus = "completed" | "failed" | "not_applicable" | "skipped";
type FindingSeverity = "info" | "warning" | "error";

interface ScoreMetric {
  name: string;
  value: number;
  unit: string | null;
}

interface ScoreFinding {
  code: string;
  message: string;
  severity: FindingSeverity;
  subject_ids: string[];
  metrics: ScoreMetric[];
}

interface ScoringGroupResult {
  group_key: string;
  status: GroupStatus;
  normalized_maximum: number;
  raw_score: number | null;
  contribution: number;
}

interface EvaluatorExecutionResult {
  evaluator_key: string;
  group_key: string;
  status: EvaluationStatus;
  raw_score: number | null;
  configured_weight: number;
  normalized_weight: number;
  contribution: number;
  threshold: number | null;
  passed_threshold: boolean | null;
  findings: ScoreFinding[];
  metrics: ScoreMetric[];
  visualization_payload:
    | EnclosedVoidsVisualizationData
    | InwardRecessVisualizationData
    | null;
}

interface EnclosedVoidsVisualizationData {
  area_tolerance: number;
  voids: Array<{
    points: Array<[number, number]>;
    area: number;
    affects_score: boolean;
  }>;
}

interface InwardRecessVisualizationData {
  maximum_length: number;
  tolerance: number;
  pockets: Array<{
    pocket_index: number;
    points: Array<[number, number]>;
    measured_length: number;
    violates_maximum: boolean;
  }>;
}

interface FloorPlanScoring {
  total_score: number;
  passed_critical: boolean;
  critical_failure: ScoreFinding | null;
  group_results: ScoringGroupResult[];
  evaluator_results: EvaluatorExecutionResult[];
  findings: ScoreFinding[];
}
```

Current `group_key` values are `critical` and `functional`. Current `evaluator_key` values are:

- `geometry_integrity`
- `required_adjacency`
- `enclosed_voids`
- `inward_recess`
- `living_room_balance`
- `bedroom_quality`
- `kitchen_dining_proximity`

Only `enclosed_voids` and `inward_recess` currently use a non-null `visualization_payload`. Clients should use `evaluator_key` as the discriminator and tolerate future evaluator and group keys.

`total_score` is a numeric quality score. `passed_critical` must be checked independently; a high total alone must not be interpreted as passing all critical checks.

### 5.4 Success response example

This shortened example keeps one room, one opening, one group, and one evaluator to show the exact nesting. Real responses contain the complete generated arrays.

```json
{
  "floor_plan": {
    "boundary": {
      "points": [
        { "x": 0.0, "y": 0.0 },
        { "x": 120.0, "y": 0.0 },
        { "x": 120.0, "y": 100.0 },
        { "x": 0.0, "y": 100.0 }
      ]
    },
    "rooms": [
      {
        "id": "bedroom_1",
        "room_type": "bedroom",
        "name": "Bedroom 1",
        "boundary": {
          "points": [
            { "x": 0.0, "y": 0.0 },
            { "x": 30.0, "y": 0.0 },
            { "x": 30.0, "y": 30.0 },
            { "x": 0.0, "y": 30.0 }
          ]
        },
        "role": "standard",
        "parent_room_id": null,
        "metadata": {
          "source_room_ids": [],
          "applied_transformations": []
        }
      }
    ],
    "openings": [
      {
        "id": "window_1",
        "opening_type": "window",
        "purpose": "daylight",
        "start": { "x": 5.0, "y": 0.0 },
        "end": { "x": 15.0, "y": 0.0 },
        "connected_room_ids": ["bedroom_1"]
      }
    ],
    "identity_redirects": {},
    "applied_transformations": ["grid_snap:v1"]
  },
  "scoring": {
    "total_score": 92.5,
    "passed_critical": true,
    "critical_failure": null,
    "group_results": [
      {
        "group_key": "critical",
        "status": "completed",
        "normalized_maximum": 50.0,
        "raw_score": 100.0,
        "contribution": 50.0
      }
    ],
    "evaluator_results": [
      {
        "evaluator_key": "geometry_integrity",
        "group_key": "critical",
        "status": "completed",
        "raw_score": 100.0,
        "configured_weight": 1.0,
        "normalized_weight": 0.25,
        "contribution": 12.5,
        "threshold": 100.0,
        "passed_threshold": true,
        "findings": [],
        "metrics": [
          {
            "name": "invalid_polygon_count",
            "value": 0.0,
            "unit": null
          }
        ],
        "visualization_payload": null
      }
    ],
    "findings": []
  }
}
```

## 6. Streaming SSE endpoint

### 6.1 Request and initial response

```http
POST /generation/stream
Content-Type: application/json
Accept: text/event-stream
```

The request body is `GenerationRequest`.

When request-body validation succeeds, the response starts as:

```http
HTTP/1.1 200 OK
Content-Type: text/event-stream; charset=utf-8
Cache-Control: no-cache, no-transform
Connection: keep-alive
X-Accel-Buffering: no
X-Generation-Job-ID: <UUID>
```

`X-Generation-Job-ID` is the ID of this newly created generation job. The same value is included in every event envelope as `job_id`.

For cross-origin browser calls, custom response headers are not currently exposed by the API's CORS configuration. A browser may therefore be unable to read `X-Generation-Job-ID`; use the first event's `job_id` instead.

### 6.2 Important SSE behavior

- This is SSE over **POST**, not GET.
- Browser `EventSource` cannot be used because it only performs GET requests and cannot send the required JSON request body. Use `fetch()` and parse `response.body`.
- One request creates one new job and one request-scoped stream.
- There is no job lookup endpoint, replay, resume, multiple-subscriber support, or `Last-Event-ID` support.
- Reposting the request creates a different job; it does not reconnect to the previous job.
- Closing or aborting the connection stops event delivery but does **not** cancel server-side generation.
- A normal stream ends immediately after exactly one terminal event: `completed` or `error`.
- If the connection closes without a terminal event, treat the operation as an indeterminate transport failure, not as success.
- Heartbeats are SSE comments and contain no JSON. They are normally emitted after about 15 seconds without a data event.
- `candidate_trial` and `progress` are throttled/coalesced, and queued non-terminal events can be dropped for a slow consumer. They are snapshots, not an audit log.
- Event `sequence` values are strictly increasing for delivered events but are not guaranteed to be contiguous. Do not treat a gap as a protocol error.
- Event order is significant. Retain received `floor_plan` events by their envelope `sequence`.

### 6.3 SSE wire format

Every data event is one SSE frame:

```text
id: 2
event: candidate_trial
data: {"schema_version":1,"sequence":2,"timestamp":"2026-07-28T10:30:00.000Z","job_id":"6b46d3c0-d20e-4ea0-a55d-6846d76d63e8","event":"candidate_trial","payload":{"trial_number":1,"trial_limit":500,"candidate_hints":[]}}

```

A heartbeat is a comment frame:

```text
: keep-alive

```

SSE frames end with a blank line. Network chunks do not correspond to frames: a chunk can contain a partial frame or multiple frames. A client must buffer decoded text until a blank-line delimiter (`\n\n` or `\r\n\r\n`) is available.

The SSE `id` field is the decimal representation of the envelope's `sequence`. The SSE `event` field is identical to the envelope's `event`.

### 6.4 Common event envelope

```ts
type GenerationEventName =
  | "status"
  | "candidate_trial"
  | "progress"
  | "floor_plan"
  | "completed"
  | "error";

interface GenerationEventEnvelope<
  E extends GenerationEventName,
  P
> {
  schema_version: 1;
  sequence: number; // Positive integer, increasing within this stream.
  timestamp: string; // UTC ISO 8601, e.g. "2026-07-28T10:30:00.000Z".
  job_id: string; // UUID string; constant for the stream.
  event: E;
  payload: P;
}
```

Clients must discriminate on `event` before reading `payload`. `schema_version` is the payload contract version; reject or explicitly handle versions other than `1`.

### 6.5 Complete discriminated event union

```ts
type GenerationSseEvent =
  | GenerationEventEnvelope<"status", StatusPayload>
  | GenerationEventEnvelope<"candidate_trial", CandidateTrialPayload>
  | GenerationEventEnvelope<"progress", ProgressPayload>
  | GenerationEventEnvelope<"floor_plan", FloorPlanPayload>
  | GenerationEventEnvelope<"completed", CompletedPayload>
  | GenerationEventEnvelope<"error", StreamErrorPayload>;

type GenerationStatus =
  | "job_started"
  | "candidate_search_started"
  | "floor_plan_generation_started"
  | "usable_floor_plan_found"
  | "presentable_floor_plan_found"
  | "timeout_reached";

interface StatusPayload {
  status: GenerationStatus;
}

interface CandidateHint {
  room_id: string;
  x: number;
  y: number;
  room_type: RoomType | null;
  hint_index: number; // Positive integer.
}

interface CandidateTrialPayload {
  trial_number: number; // One-based completed-trial count.
  trial_limit: number;  // Positive maximum; currently 500.
  candidate_hints: CandidateHint[];
}

interface ProgressPayload {
  stage: string;        // Currently "candidate_search".
  trial_number: number; // One-based completed-trial count.
  trial_limit: number;  // Positive maximum; currently 500.
  elapsed_ms: number;   // Non-negative elapsed milliseconds.
  timeout_ms: number;   // Positive configured search timeout; currently 60000.
}

type FloorPlanClassification = "usable" | "presentable";

interface FloorPlanPayload {
  classification: FloorPlanClassification;
  trial_number: number | null; // One-based source trial; null if search is disabled.
  candidate_id: number;        // One-based eligible-candidate ID.
  solver_run_id: number;       // One-based solver run ID for this candidate.
  score: number;
  passed_critical: boolean;
  floor_plan: FloorPlan;
}

type CompletionOutcome =
  | "presentable_plan_found"
  | "best_usable_plan_returned";

interface CompletedPayload {
  outcome: CompletionOutcome;
  final_floor_plan_sequence: number | null;
  elapsed_ms: number;
}

interface StreamErrorPayload {
  stage: string;
  code: string;
  message: string;
  recoverable: boolean; // Currently false for terminal generation errors.
}
```

### 6.6 Event meanings and client actions

#### `status`

A machine-readable state notification. Status events can repeat, especially `floor_plan_generation_started`, because multiple candidates may be attempted.

Possible payloads:

```json
{ "status": "job_started" }
```

```json
{ "status": "candidate_search_started" }
```

```json
{ "status": "floor_plan_generation_started" }
```

```json
{ "status": "usable_floor_plan_found" }
```

```json
{ "status": "presentable_floor_plan_found" }
```

```json
{ "status": "timeout_reached" }
```

`timeout_reached` does not necessarily mean failure. If a usable plan was found before timeout, it can be followed by `completed` with `best_usable_plan_returned`. If no usable plan exists, it is followed by `error`.

#### `candidate_trial`

Reports a completed candidate-search trial and its candidate hint coordinates:

```json
{
  "trial_number": 12,
  "trial_limit": 500,
  "candidate_hints": [
    {
      "room_id": "bedroom_1",
      "x": 40.0,
      "y": 60.0,
      "room_type": null,
      "hint_index": 1
    }
  ]
}
```

This event is informational. Do not assume one event will arrive for every trial.

#### `progress`

Reports bounded candidate-search counters and time:

```json
{
  "stage": "candidate_search",
  "trial_number": 12,
  "trial_limit": 500,
  "elapsed_ms": 1840,
  "timeout_ms": 60000
}
```

This is not a reliable overall completion percentage. Candidate search can stop early, and floor-plan solving/scoring work is not represented by `trial_number / trial_limit`. It is safe to display trial progress and elapsed time separately.

#### `floor_plan`

Reports a client-ready floor plan, including generated openings:

```json
{
  "classification": "usable",
  "trial_number": 148,
  "candidate_id": 1,
  "solver_run_id": 1,
  "score": 84.25,
  "passed_critical": true,
  "floor_plan": {
    "boundary": { "points": [] },
    "rooms": [],
    "openings": [],
    "identity_redirects": {},
    "applied_transformations": []
  }
}
```

The empty geometry arrays above only abbreviate the example; actual usable/presentable plans contain geometry.

There may be multiple `usable` floor-plan events as better usable plans are found. A `presentable` floor-plan event is immediately followed by successful completion.

The SSE endpoint does **not** send the complete `FloorPlanScoring` object from `POST /generation`. It sends only `score` and `passed_critical` with each plan. There is no later result-retrieval endpoint. Use the synchronous endpoint instead if the client requires all scoring groups, evaluators, findings, and metrics.

#### `completed`

The successful terminal event:

```json
{
  "outcome": "presentable_plan_found",
  "final_floor_plan_sequence": 42,
  "elapsed_ms": 23880
}
```

or:

```json
{
  "outcome": "best_usable_plan_returned",
  "final_floor_plan_sequence": 31,
  "elapsed_ms": 60017
}
```

`final_floor_plan_sequence` identifies the envelope `sequence` of the selected `floor_plan` event. The client must retain floor-plan events by sequence and select this exact one when completion arrives. The field is nullable at the protocol level; if it is `null` or does not identify a floor plan received by the client, treat the result as incomplete and do not guess which plan is final.

No events follow `completed`.

#### `error`

The failed terminal event:

```json
{
  "stage": "preprocessing",
  "code": "business_rule_error",
  "message": "Missing mandatory room type(s): bedroom, kitchen",
  "recoverable": false
}
```

No events follow `error`. `recoverable: false` means this stream/job cannot continue. The user may correct a request error and start a new request, but that is a new job.

### 6.7 Browser implementation

```ts
type EventHandler = (event: GenerationSseEvent) => void;

async function streamGeneration(
  baseUrl: string,
  request: GenerationRequest,
  onEvent: EventHandler,
  signal?: AbortSignal,
): Promise<FloorPlanPayload> {
  const response = await fetch(`${baseUrl}/generation/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "text/event-stream",
    },
    body: JSON.stringify(request),
    signal,
  });

  if (!response.ok) {
    // This includes request-shape validation errors returned before SSE starts.
    const contentType = response.headers.get("content-type") ?? "";
    const errorBody = contentType.includes("application/json")
      ? await response.json()
      : await response.text();
    throw new Error(`Generation HTTP ${response.status}: ${JSON.stringify(errorBody)}`);
  }

  if (!response.body) {
    throw new Error("The browser did not expose the streaming response body.");
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.toLowerCase().startsWith("text/event-stream")) {
    throw new Error(`Expected text/event-stream, received ${contentType || "unknown"}.`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  const floorPlans = new Map<number, FloorPlanPayload>();
  let buffer = "";
  let terminalReceived = false;

  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });

      const frames = buffer.split(/\r?\n\r?\n/);
      buffer = frames.pop() ?? "";

      for (const frame of frames) {
        const lines = frame.split(/\r?\n/);

        // Empty frames and heartbeat/comment-only frames carry no event data.
        const data = lines
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).replace(/^ /, ""))
          .join("\n");
        if (!data) continue;

        const event = JSON.parse(data) as GenerationSseEvent;
        if (event.schema_version !== 1) {
          throw new Error(`Unsupported SSE schema version: ${event.schema_version}`);
        }

        onEvent(event);

        if (event.event === "floor_plan") {
          floorPlans.set(event.sequence, event.payload);
        } else if (event.event === "error") {
          terminalReceived = true;
          throw new Error(
            `${event.payload.stage}/${event.payload.code}: ${event.payload.message}`,
          );
        } else if (event.event === "completed") {
          terminalReceived = true;
          const sequence = event.payload.final_floor_plan_sequence;
          const selected = sequence === null ? undefined : floorPlans.get(sequence);
          if (!selected) {
            throw new Error("Completion did not reference a received floor-plan event.");
          }
          return selected;
        }
      }

      if (done) break;
    }
  } finally {
    await reader.cancel().catch(() => undefined);
  }

  if (!terminalReceived) {
    throw new Error("SSE connection closed before a terminal event.");
  }
  throw new Error("Generation ended without a selected floor plan.");
}
```

An `AbortController` can stop local delivery:

```ts
const controller = new AbortController();

const resultPromise = streamGeneration(
  "http://127.0.0.1:8001",
  generationRequest,
  (event) => console.log(event.event, event.payload),
  controller.signal,
);

// Stops this client's HTTP stream; it does not cancel server computation.
controller.abort();
```

### 6.8 Command-line example

Use `--no-buffer` so frames are displayed immediately:

```bash
curl --no-buffer --fail-with-body \
  -X POST 'http://127.0.0.1:8001/generation/stream' \
  -H 'Accept: text/event-stream' \
  -H 'Content-Type: application/json' \
  --data-binary '{
    "floor_limits": {
      "max_width": 120,
      "max_length": 100
    },
    "aspect_ratio": "4:3",
    "rooms": [
      {"id":"bedroom_1","room_type":"bedroom","requested_size":"regular"},
      {"id":"bathroom_1","room_type":"bathroom","requested_size":"regular"},
      {"id":"kitchen_1","room_type":"kitchen","requested_size":"regular"},
      {"id":"veranda_1","room_type":"veranda","requested_size":"regular"}
    ]
  }'
```

## 7. Errors and validation

Errors fall into three different wire formats. Clients must support all applicable formats.

### 7.1 Request-shape validation: HTTP 422

Request parsing and structural validation happen before either endpoint handler starts.

```http
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/json
```

```ts
interface HttpValidationError {
  detail: ValidationIssue[];
}

interface ValidationIssue {
  type: string;
  loc: Array<string | number>;
  msg: string;
  input?: unknown;
  ctx?: Record<string, unknown>;
}
```

Example:

```json
{
  "detail": [
    {
      "type": "greater_than",
      "loc": ["body", "floor_limits", "max_width"],
      "msg": "Input should be greater than 0",
      "input": 0,
      "ctx": { "gt": 0.0 }
    },
    {
      "type": "enum",
      "loc": ["body", "rooms", 0, "room_type"],
      "msg": "Input should be 'bedroom', 'bathroom', 'attached_bathroom', 'living_room', 'kitchen', 'dining_room', 'hallway', 'veranda', 'garage' or 'open_area'",
      "input": "Garage",
      "ctx": {
        "expected": "'bedroom', 'bathroom', 'attached_bathroom', 'living_room', 'kitchen', 'dining_room', 'hallway', 'veranda', 'garage' or 'open_area'"
      }
    }
  ]
}
```

Common structural validation messages:

| Condition | `type` | `msg` |
|---|---|---|
| Required field omitted | `missing` | `Field required` |
| Width or length is `0` or negative | `greater_than` | `Input should be greater than 0` |
| Unknown property inside `floor_limits` | `extra_forbidden` | `Extra inputs are not permitted` |
| Invalid `room_type` | `enum` | `Input should be 'bedroom', 'bathroom', 'attached_bathroom', 'living_room', 'kitchen', 'dining_room', 'hallway', 'veranda', 'garage' or 'open_area'` |
| `requested_size` is `""` | `string_too_short` | `String should have at least 1 character` |
| `rooms` is empty | `too_short` | `List should have at least 1 item after validation, not 0` |
| `aspect_ratio` is neither a number nor a string | `float_type` and `string_type` issues | `Input should be a valid number` / `Input should be a valid string` |
| Malformed JSON | `json_invalid` | `JSON decode error` |

Use `loc` and `type` for programmatic field mapping. Display `msg` as the default validation message, but do not branch application logic on the English wording.

### 7.2 Synchronous generation failure: HTTP 422

When the JSON shape is valid but generation rejects the input or cannot produce a usable plan, `POST /generation` returns:

```http
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/json
```

```ts
interface GenerationErrorResponse {
  stage: GenerationErrorStage;
  code: string;
  message: string;
  details: Record<string, unknown> | null;
}

type GenerationErrorStage =
  | "preprocessing"
  | "candidate_search"
  | "candidate_scoring"
  | "solver"
  | "refinement"
  | "post_processing"
  | "openings"
  | "attempt_scoring"
  | "scoring"
  | "visualization"
  | "final_validation";
```

Example:

```json
{
  "stage": "preprocessing",
  "code": "business_rule_error",
  "message": "Missing mandatory room type(s): bedroom, kitchen",
  "details": null
}
```

### 7.3 Streaming generation failure: terminal SSE `error`

After `POST /generation/stream` has returned HTTP 200 and started SSE, later failures cannot change the HTTP status. They are sent as a terminal `error` event:

```json
{
  "schema_version": 1,
  "sequence": 4,
  "timestamp": "2026-07-28T10:30:00.000Z",
  "job_id": "6b46d3c0-d20e-4ea0-a55d-6846d76d63e8",
  "event": "error",
  "payload": {
    "stage": "preprocessing",
    "code": "business_rule_error",
    "message": "Missing mandatory room type(s): bedroom, kitchen",
    "recoverable": false
  }
}
```

The stream error does not include the synchronous response's `details` object.

### 7.4 Client-correctable semantic errors

These errors occur after the request JSON has passed structural validation. For the synchronous endpoint they use `GenerationErrorResponse`; for SSE they use a terminal `error` payload.

| Stage | Code | Message or message pattern | Client correction |
|---|---|---|---|
| `preprocessing` | `normalization_error` | `aspect_ratio must use the H:W form` | Send a number or exactly two numeric parts separated by `:`. |
| `preprocessing` | `normalization_error` | `aspect_ratio H:W parts must be numeric` | Make both ratio parts numeric. |
| `preprocessing` | `normalization_error` | `aspect_ratio width part cannot be zero` | Use a non-zero W part. |
| `preprocessing` | `normalization_error` | `aspect_ratio must be finite and greater than zero` | Send a finite positive ratio. |
| `preprocessing` | `input_validation_error` | `aspect_ratio must be between 0.5 and 2.0 inclusive` | Keep the evaluated ratio in the supported range. |
| `preprocessing` | `input_validation_error` | `Duplicate room ID(s): <ids>` | Assign a unique non-blank ID to each room or omit IDs for automatic generation. |
| `preprocessing` | `input_validation_error` | `Requested <N> attached bathroom(s), but only <M> bedroom(s) were provided. Each attached bathroom requires a unique bedroom.` | Add bedrooms or remove attached bathrooms. |
| `preprocessing` | `business_rule_error` | `Missing mandatory room type(s): <types>` | Include at least one bedroom, bathroom, kitchen, and veranda. |
| `preprocessing` | `business_rule_error` | `Only one living room is supported` | Supply zero or one living room. |
| `preprocessing` | `room_preparation_error` | `Room '<id>' (<type>) has no size reference for '<size>'` | Use `requested_size: "regular"` or omit it. |
| `preprocessing` | `floor_preparation_error` | `The largest permitted floor at the requested aspect ratio has area <actual>, below the required minimum <required>` | Increase floor limits, change aspect ratio, or request fewer rooms. |
| `preprocessing` | `floor_preparation_error` | `Selected floor cannot contain minimum dimensions for room(s): <ids>` | Increase floor limits/change aspect ratio or remove the listed rooms. |
| `preprocessing` | `floor_preparation_error` | `Selected floor cannot contain the configured hallway dimensions` | Increase the permitted floor dimensions. |
| `final_validation` | `no_floor_plan_found` | `No usable floor plan was found before the pipeline stopped.` | Retry with less restrictive input or larger floor limits. Inspect `details` on the synchronous endpoint for the termination reason. |

For `no_floor_plan_found`, synchronous `details` has this shape:

```ts
interface NoFloorPlanFoundDetails {
  termination_reason:
    | "timeout"
    | "candidate_trials_exhausted"
    | "default_candidate_exhausted";
  timeout_seconds: number;
  elapsed_seconds: number;
  eligible_candidate_count: number;
  solver_failure_count: number;
  last_solver_failure: {
    stage: string;
    code: string;
    message: string;
  } | null;
}
```

The API may return additional stage-specific codes when solving, refinement, post-processing, opening generation, or scoring cannot complete. Clients must treat `stage` and `code` as machine-readable strings, show the safe `message`, and avoid assuming the tables above are exhaustive.

### 7.5 Unexpected server failure

For `POST /generation`, an unexpected unhandled failure returns:

```http
HTTP/1.1 500 Internal Server Error
Content-Type: application/json
```

```json
{
  "message": "Generation failed unexpectedly."
}
```

For `POST /generation/stream`, an unexpected failure after the stream starts is:

```json
{
  "stage": "generation",
  "code": "unexpected_generation_error",
  "message": "Generation failed unexpectedly.",
  "recoverable": false
}
```

Transport, proxy, and gateway errors can use a non-API response body. For any non-2xx response, inspect `Content-Type` before attempting JSON parsing.

## 8. Client integration checklist

- Send only canonical lowercase `RoomType` values.
- Use project units (`10` units per meter) for floor limits and all rendered response geometry.
- Configure an HTTP timeout longer than generation and configure proxies not to buffer SSE.
- Use synchronous `POST /generation` when the full scoring report is required.
- Use `fetch()` streaming, not browser `EventSource`, for `POST /generation/stream`.
- Check the HTTP status before reading SSE.
- Buffer arbitrary network chunks and split only on SSE blank-line boundaries.
- Ignore heartbeat/comment frames.
- Validate `schema_version === 1`.
- Discriminate payloads using the envelope `event`.
- Do not expect all trial/progress events or contiguous sequence numbers.
- Retain floor plans by envelope `sequence`.
- On `completed`, select `final_floor_plan_sequence`; do not simply select the last rendered plan.
- Treat `error` as terminal failure.
- Treat EOF without `completed` or `error` as a transport failure with unknown job outcome.
- Do not automatically reconnect with `Last-Event-ID`; replay/resume is unsupported.
- Remember that aborting the HTTP stream does not cancel generation on the server.

## 9. Deployment requirements for browser SSE

When the client runs on a different origin:

1. Add the exact client origin to the server's comma-separated `CORS_ORIGINS` setting.
2. Expose the server through HTTPS when the client page uses HTTPS; browsers block mixed active content.
3. Disable response buffering on the reverse proxy for `/generation/stream`.
4. Keep proxy read/idle timeouts longer than the generation duration and heartbeat interval.
5. Avoid intermediary response transformations or compression that delay individual frames.
6. Do not expose this unauthenticated API directly to the public internet without an authenticated gateway or equivalent access control.

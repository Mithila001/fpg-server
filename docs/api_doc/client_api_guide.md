# House Plan Generator API Guide

This document describes how to use the local FastAPI server as a client. It focuses on the request and response shapes that a frontend or other client needs to understand.

## Base URL

Local development default:

```text
http://localhost:8000
```

All endpoints described below are under the `/algorithms` prefix.

## Transport And Headers

Use JSON for normal requests:

```http
Content-Type: application/json
Accept: application/json
```

For Server-Sent Events, use:

```http
Accept: text/event-stream
```

Optional request header:

```http
X-Client-Id: your-client-id
```

If `X-Client-Id` is provided, the server uses it to identify the client. If it is omitted, the server falls back to the request IP address when available.

## Shared Job Model

The algorithm endpoints are asynchronous. A `POST` request accepts the job and returns a `job_id`. The client then polls the job status endpoint or subscribes to the SSE stream.

### Job Status Values

The server currently uses these job states:

- `SEARCHING` - the job is running
- `COMPLETED` - the job finished successfully
- `TERMINATED` - the job was cancelled
- `TIMED_OUT` - the job exceeded the server timeout

### Job State Response Shape

This is the common payload returned by job status endpoints and cancellation responses:

```json
{
  "job_id": "string",
  "job_kind": "FORMAT_V2 | BUILDABLE_SPACE",
  "client_key": "string",
  "pid": 1234,
  "status": "SEARCHING | COMPLETED | TERMINATED | TIMED_OUT",
  "created_at": "2026-05-04T12:00:00+00:00",
  "updated_at": "2026-05-04T12:00:05+00:00",
  "events": [
    {
      "id": 1,
      "timestamp": "2026-05-04T12:00:01+00:00",
      "event": "JOB_STARTED",
      "message": "Job accepted and running.",
      "data": {
        "status": "SEARCHING"
      }
    }
  ],
  "result": {}
}
```

The `events` array is append-only and contains the job history. The `result` field is `null` while the job is running, then becomes the final algorithm payload after completion.

## 1) Submit Floor Plan Job

### `POST /algorithms/format/v2`

Submits a floor-plan generation job.

### Request Body

```json
{
  "floor_width": 150,
  "floor_height": 150,
  "aspect_ratio": "1:1",
  "room_template": {
    "name": "Standard 2BHK Layout",
    "data": [
      {
        "id": "bedroom1",
        "type": "bedroom",
        "size": "regular"
      }
    ]
  },
  "should_optuna_run": true,
  "optuna_trial_count": 500
}
```

### Request Fields

- `floor_width` - number, required. Floor width in centimeters.
- `floor_height` - number, required. Floor height in centimeters.
- `aspect_ratio` - number or string, required.
- `room_template` - object, required.
- `should_optuna_run` - boolean, optional, default `false`.
- `optuna_trial_count` - integer, optional, default `20`.

### `aspect_ratio` Rules

The server accepts either:

- a numeric ratio, for example `1.5`
- a string in `H:W` form, for example `"2:1"`

The server normalizes the value to `H / W` and requires the final value to be between `0.5` and `2.0` inclusive.

### `room_template` Shape

`room_template` uses the shared room template model:

```json
{
  "name": "Template name",
  "data": [
    {
      "id": "room1",
      "type": "bedroom",
      "size": "regular"
    }
  ]
}
```

Notes:

- `name` is required.
- `data` is required and is an array of room descriptors.
- Each item in `data` is passed through to the solver as-is.
- The server does not enforce a single fixed item schema at this layer, but the solver expects fields such as `id`, `type`, and `size`.

### Success Response

HTTP `202 Accepted`

```json
{
  "job_id": "2c0f1d6f-6a55-4e73-8c17-6b7d2b9a1a88",
  "status": "SEARCHING",
  "message": "Job accepted for processing."
}
```

### Conflict Response

HTTP `409 Conflict`

Returned when the same client already has a running job.

```json
{
  "detail": "Process is Already Running"
}
```

### Final Job Result

Poll `GET /algorithms/job/{job_id}` or listen to SSE to receive the final result. On completion, `result` contains the serialized solver output.

For this endpoint, the final payload has this top-level shape:

```json
{
  "status": "COMPLETED",
  "message": "Job finished processing.",
  "union_results": {
    "floor_plan_with_openings": {
      "floor_plan": [],
      "openings": []
    },
    "unified_floor_plan": {
      "walls": [],
      "total_wall_length": 0.0
    }
  }
}
```

The exact nested geometry depends on the generated plan.

## 2) Submit Buildable-Space Job

### `POST /algorithms/buildable-space`

Submits a land-parcel buildable-space job.

### Request Body

```json
{
  "area": 100000,
  "segmentsCoordinates": [
    { "x": 136.35, "y": 136.52 },
    { "x": 483.03, "y": 209.93 },
    { "x": 519.74, "y": 523.98 }
  ],
  "roadConnected": [
    {
      "segment": [
        { "x": 483.03, "y": 209.93 },
        { "x": 519.74, "y": 523.98 }
      ],
      "roadType": "mainRoad"
    }
  ],
  "min_width": 100,
  "min_height": 100,
  "should_plot": true
}
```

### Request Fields

- `area` - number, required.
- `segmentsCoordinates` - array of coordinate points, required, minimum 3 points.
- `roadConnected` - array of road connection objects, optional, default `[]`.
- `min_width` - number, optional, default `100`.
- `min_height` - number, optional, default `100`.
- `should_plot` - boolean, optional, default `false`.

### Coordinate Payload

```json
{ "x": 123.4, "y": 567.8 }
```

### Road Connection Payload

```json
{
  "segment": [
    { "x": 1, "y": 2 },
    { "x": 3, "y": 4 }
  ],
  "roadType": "mainRoad"
}
```

### Success Response

HTTP `202 Accepted`

```json
{
  "job_id": "8a631d5e-8a0c-4e7f-9cb2-4b5de8d3c2d0",
  "status": "SEARCHING",
  "message": "Job accepted for processing."
}
```

### Final Result Shape

The buildable-space job returns a normalized payload in `result`:

```json
{
  "status": "OK",
  "message": "Buildable space computed successfully.",
  "buildable_rectangle": {
    "vertices": [
      { "x": 10, "y": 20 },
      { "x": 30, "y": 20 },
      { "x": 30, "y": 40 },
      { "x": 10, "y": 40 }
    ],
    "width": 20,
    "height": 20,
    "area": 400
  },
  "shrunk_boundary": [
    { "x": 1, "y": 2 }
  ],
  "metadata": {}
}
```

If no feasible rectangle is found, `buildable_rectangle` becomes `null` while the job still returns `status: "OK"`.

If the server cannot process the land payload, the error payload uses this shape:

```json
{
  "status": "ERROR",
  "message": "Reason for failure",
  "buildable_rectangle": null,
  "shrunk_boundary": null,
  "metadata": null
}
```

## 3) Get Active Job For Client

### `GET /algorithms/job/active`

Returns the currently running job for the caller client, if any.

### Success Response

HTTP `200 OK`

```json
{
  "job_id": "2c0f1d6f-6a55-4e73-8c17-6b7d2b9a1a88",
  "job_kind": "FORMAT_V2",
  "client_key": "127.0.0.1",
  "pid": 1234,
  "status": "SEARCHING",
  "created_at": "2026-05-04T12:00:00+00:00",
  "updated_at": "2026-05-04T12:00:05+00:00",
  "events": [],
  "result": null
}
```

### Not Found Response

HTTP `404 Not Found`

```json
{
  "detail": "No active job found."
}
```

## 4) Get Job Status

### `GET /algorithms/job/{job_id}`

Returns the current stored state of a specific job.

### Success Response

HTTP `200 OK`

```json
{
  "job_id": "2c0f1d6f-6a55-4e73-8c17-6b7d2b9a1a88",
  "job_kind": "FORMAT_V2",
  "client_key": "127.0.0.1",
  "pid": 1234,
  "status": "COMPLETED",
  "created_at": "2026-05-04T12:00:00+00:00",
  "updated_at": "2026-05-04T12:00:30+00:00",
  "events": [
    {
      "id": 1,
      "timestamp": "2026-05-04T12:00:01+00:00",
      "event": "JOB_STARTED",
      "message": "Job accepted and running.",
      "data": {
        "status": "SEARCHING"
      }
    },
    {
      "id": 2,
      "timestamp": "2026-05-04T12:00:30+00:00",
      "event": "COMPLETED",
      "message": "Job finished processing.",
      "data": {
        "status": "COMPLETED",
        "result": {}
      }
    }
  ],
  "result": {}
}
```

### Not Found Response

HTTP `404 Not Found`

```json
{
  "detail": "Job not found."
}
```

## 5) Cancel A Job

### `POST /algorithms/cancel`

Cancels the current active job for the caller client, or cancels the specified job.

### Request Body

```json
{
  "job_id": "2c0f1d6f-6a55-4e73-8c17-6b7d2b9a1a88"
}
```

The `job_id` field is optional. If omitted, the server cancels the currently active job for that client.

### Success Response

HTTP `200 OK`

```json
{
  "cancelled": true,
  "message": "Job cancelled successfully.",
  "job": {
    "job_id": "2c0f1d6f-6a55-4e73-8c17-6b7d2b9a1a88",
    "job_kind": "FORMAT_V2",
    "client_key": "127.0.0.1",
    "pid": 1234,
    "status": "TERMINATED",
    "created_at": "2026-05-04T12:00:00+00:00",
    "updated_at": "2026-05-04T12:00:10+00:00",
    "events": [],
    "result": null
  }
}
```

### No Active Job

If no `job_id` is provided and the client has no active job, the server returns HTTP `409 Conflict`:

```json
{
  "detail": "No active job found."
}
```

### Missing Job ID

If a `job_id` is provided but does not exist, the server returns HTTP `404 Not Found`:

```json
{
  "detail": "Job not found."
}
```

### Already Finished Job

If the job already finished, was cancelled, or timed out, the server returns HTTP `404 Not Found` when a `job_id` was supplied, or `409 Conflict` when cancelling by active client job.

Example message:

```json
{
  "detail": "Job is already COMPLETED."
}
```

## 6) Stream Job Events With SSE

### `GET /algorithms/job/{job_id}/events`

This endpoint streams job updates using Server-Sent Events.

Use this when you want live progress updates without polling.

### Request Headers

```http
Accept: text/event-stream
```

Optional reconnect support:

```http
Last-Event-ID: 4
```

You can also pass a query parameter:

```text
/algorithms/job/{job_id}/events?last_event_id=4
```

The server uses the header first, then the query parameter, and falls back to `0` if neither is present.

### SSE Event Format

Each event is sent in standard SSE format:

```text
id: 2
event: job_progress
data: {"id":2,"event":"job_progress","message":"...","timestamp":"...","data":{}}

```

### SSE Data Payload Shape

The `data:` field always contains a JSON object with this structure:

```json
{
  "id": 2,
  "event": "job_progress",
  "message": "Progress update.",
  "timestamp": "2026-05-04T12:00:12+00:00",
  "data": {}
}
```

### Known SSE Event Names

The backend currently emits these event names directly or indirectly:

- `JOB_STARTED`
- `job_progress`
- `generation_success`
- `generation_failed`
- `COMPLETED`
- `TERMINATED`
- `TIMED_OUT`
- `job_missing`

The exact progress event names inside `data.event` may vary by algorithm stage. Client code should treat them as backend-defined strings and rely on the envelope fields `id`, `event`, `message`, `timestamp`, and `data`.

### Keepalive

While a job is still running and no new event is ready, the server sends:

```text
: keepalive

```

This is an SSE comment line and can be ignored by the client.

### Job Missing Event

If the job no longer exists while streaming, the server sends:

```text
event: job_missing
data: {"message": "Job not found."}

```

### Client Consumption Example

Browser JavaScript:

```javascript
const jobId = "2c0f1d6f-6a55-4e73-8c17-6b7d2b9a1a88";
const stream = new EventSource(`/algorithms/job/${jobId}/events`);

stream.onmessage = (event) => {
  const payload = JSON.parse(event.data);
  console.log("event", payload.event, payload.message, payload.data);
};

stream.addEventListener("job_missing", (event) => {
  console.error("Job disappeared", JSON.parse(event.data));
  stream.close();
});
```

If the client reconnects after a drop, send `Last-Event-ID` so the server can resume from the last received event.

## Client Flow Summary

A typical client flow is:

1. Submit a job with `POST /algorithms/format/v2` or `POST /algorithms/buildable-space`.
2. Store the returned `job_id`.
3. Either poll `GET /algorithms/job/{job_id}` or open `GET /algorithms/job/{job_id}/events`.
4. Read the final `result` when `status` becomes `COMPLETED`.
5. Cancel with `POST /algorithms/cancel` if the user stops the job.

## Practical Notes For Local Development

- The server is intended to run locally on `localhost:8000`.
- The backend CORS configuration already allows a frontend on `http://localhost:5173` and `http://127.0.0.1:5173`.
- A client should always treat `result` as algorithm-specific and read the top-level `status` and `message` first.
- If the job is still running, expect `result: null` and use SSE or polling for updates.

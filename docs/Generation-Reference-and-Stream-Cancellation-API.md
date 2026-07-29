# Generation Reference and Stream Cancellation API

This document describes the two generation API additions available to client applications:

1. Reading the room-size constraints accepted by floor-plan generation.
2. Cancelling an active streamed floor-plan generation job.

## Measurement Units

All dimensional and area values use project units.

- `10` project units = `1 meter`
- Width values are project units.
- Area values are square project units.

Clients should use the values returned by the server rather than maintaining a separate copy of the room-size configuration.

---

## 1. Get Room-Size Constraints

Returns the validated room-size constraints currently used by the generation preprocessing pipeline.

### Request

```http
GET /generation/room-size-constraints
Accept: application/json
```

No request body is required.

### Successful Response

```http
200 OK
Content-Type: application/json
```

```json
{
  "room_size_constraints": [
    {
      "room_type": "bedroom",
      "size": "regular",
      "min_width": 30.0,
      "max_width": 50.0,
      "min_area": 900.0,
      "max_area": 1800.0
    }
  ]
}
```

The values above are an example. The client must use the values returned by the running server.

### Response Fields

| Field | Type | Description |
|---|---|---|
| `room_size_constraints` | array | Available room type and size combinations. |
| `room_type` | string | Canonical room type used by the generation API. |
| `size` | string | Size name accepted by `rooms[].requested_size`. |
| `min_width` | number | Minimum permitted room width. |
| `max_width` | number | Maximum permitted room width. |
| `min_area` | number | Minimum permitted room area. |
| `max_area` | number | Maximum permitted room area. |

Canonical room-type values are:

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
open_area
```

Only combinations returned by the endpoint should be presented as selectable room sizes.

### Using a Returned Size

The returned `size` value is passed as `requested_size` when starting generation:

```json
{
  "room_type": "bedroom",
  "name": "Bedroom 1",
  "requested_size": "regular",
  "required": true
}
```

### Error Response

```http
500 Internal Server Error
Content-Type: application/json
```

```json
{
  "message": "Generation room-size constraints are currently unavailable."
}
```

This means the server could not load or validate its generation reference data.

---

## 2. Cancel a Streamed Generation Job

Cancels a job started through:

```http
POST /generation/stream
```

This endpoint does not cancel the non-streaming `POST /generation` request.

### Obtain the Job ID

The stream-start response contains the job ID in this response header:

```http
X-Generation-Job-ID: <job-id>
```

The client must retain this value while the generation stream is active.

For cross-origin browser clients, the backend CORS configuration must expose the `X-Generation-Job-ID` response header.

### Cancellation Request

```http
DELETE /generation/stream/{job_id}
Accept: application/json
```

Example:

```http
DELETE /generation/stream/61d35e8d-6878-4c82-b32e-d6365c0b50cc
```

No request body is required.

### Cancellation Accepted

```http
202 Accepted
Content-Type: application/json
```

```json
{
  "job_id": "61d35e8d-6878-4c82-b32e-d6365c0b50cc",
  "status": "cancellation_requested"
}
```

`202 Accepted` means the cancellation signal was accepted. The SSE stream is sent a terminal `cancelled` event and closed. Server-side cancellation is cooperative, so a solver or refinement operation already running may finish its current call before the pipeline fully exits.

### Cancellation Already Requested

A repeated request for the same active job returns:

```http
200 OK
Content-Type: application/json
```

```json
{
  "job_id": "61d35e8d-6878-4c82-b32e-d6365c0b50cc",
  "status": "already_requested"
}
```

### Job Not Found

```http
404 Not Found
Content-Type: application/json
```

```json
{
  "message": "No active streamed generation job was found."
}
```

This occurs when:

- the job ID is invalid,
- the generation job has already completed,
- the generation job has already failed, or
- the active job is no longer registered by the server.

### Terminal SSE Event

When the cancellation request is accepted, the stream sends a terminal `cancelled` event and closes.

```text
event: cancelled
data: {"schema_version":1,"sequence":12,"timestamp":"2026-07-29T11:30:00.000Z","job_id":"61d35e8d-6878-4c82-b32e-d6365c0b50cc","event":"cancelled","payload":{"reason":"client_request"}}
```

The client should treat `cancelled` as a terminal event, like `completed` or `error`.

Closing the HTTP connection by itself does not guarantee that server-side generation is cancelled. Use the cancellation endpoint when the user explicitly stops generation.

---

## Browser Example

The generation stream uses a `POST` request, so a browser client normally reads it with `fetch()` rather than the native `EventSource` constructor.

```javascript
let activeGenerationJobId = null;
let streamAbortController = null;

export async function startGeneration(requestBody) {
  streamAbortController = new AbortController();

  const response = await fetch("/generation/stream", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "text/event-stream"
    },
    body: JSON.stringify(requestBody),
    signal: streamAbortController.signal
  });

  if (!response.ok) {
    throw new Error(`Generation stream failed: ${response.status}`);
  }

  activeGenerationJobId = response.headers.get("X-Generation-Job-ID");
  if (!activeGenerationJobId) {
    throw new Error("Generation job ID was not returned by the server.");
  }

  return response.body;
}

export async function cancelGeneration() {
  if (!activeGenerationJobId) {
    return null;
  }

  const response = await fetch(
    `/generation/stream/${encodeURIComponent(activeGenerationJobId)}`,
    {
      method: "DELETE",
      headers: {
        "Accept": "application/json"
      }
    }
  );

  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload.message ?? "Could not cancel generation.");
  }

  return payload;
}
```

The client should continue reading the stream until it receives `cancelled`, `completed`, or `error`.

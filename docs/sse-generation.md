# Floor-plan generation SSE

The streaming API is an opt-in alternative to the existing synchronous
`POST /generation` endpoint:

```text
POST /generation/stream
Content-Type: application/json
Accept: text/event-stream
```

It accepts the same JSON request and returns progress and result events as they
become available. The final event is either `completed` or `error`.

This first version is a request-scoped stream. It does not provide event replay,
reconnection, cancellation, a job lookup API, or multiple subscribers. Closing
the connection stops delivery but does not stop server-side generation.

## Start the server

Docker Compose publishes the container's port `8000` on host port `8001`:

```bash
docker compose up --build
```

The Docker URL is:

```text
http://127.0.0.1:8001
```

A directly launched Uvicorn process normally uses
`http://127.0.0.1:8000`.

## Inspect the stream with curl

Use `--no-buffer` so curl displays frames as soon as they arrive:

```bash
curl --no-buffer --fail-with-body \
  -X POST 'http://127.0.0.1:8001/generation/stream' \
  -H 'Accept: text/event-stream' \
  -H 'Content-Type: application/json' \
  --data-binary '{
    "floor_limits": {
      "max_width": 120.0,
      "max_length": 100.0
    },
    "aspect_ratio": "4:3",
    "rooms": [
      {
        "id": "bedroom_1",
        "room_type": "bedroom",
        "requested_size": "regular"
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
  }'
```

The response is framed using standard SSE fields:

```text
id: 1
event: status
data: {"schema_version":1,"sequence":1,"timestamp":"...","job_id":"...","event":"status","payload":{"status":"job_started"}}

: keep-alive

id: 2
event: candidate_trial
data: {"schema_version":1,"sequence":2,"timestamp":"...","job_id":"...","event":"candidate_trial","payload":{...}}
```

Heartbeat comments keep an otherwise idle connection active. Event data always
uses this envelope:

```json
{
  "schema_version": 1,
  "sequence": 2,
  "timestamp": "2026-07-27T10:30:00.000Z",
  "job_id": "generation UUID",
  "event": "candidate_trial",
  "payload": {}
}
```

The job ID is also returned in the `X-Generation-Job-ID` response header.
Request validation failures are normal HTTP `422` JSON responses. Failures
after streaming begins are terminal `error` events on the HTTP `200` stream.

## Event types

- `status`: a stable machine-readable generation state.
- `candidate_trial`: the one-based trial number, trial limit, and canonical
  candidate hint points. High-frequency trials are coalesced.
- `progress`: bounded trial/time progress. This is not an overall completion
  percentage.
- `floor_plan`: a usable or presentable client-ready plan, including openings,
  its score, and candidate/run identity.
- `completed`: successful terminal outcome and the selected floor-plan event
  sequence.
- `error`: safe terminal stage, code, message, and recoverability flag.

No normal events follow `completed` or `error`.

## Consume the stream in browser JavaScript

Native `EventSource` only issues GET requests and cannot send the required
generation JSON body. Use `fetch()` and read its response stream:

```javascript
const response = await fetch("http://127.0.0.1:8001/generation/stream", {
  method: "POST",
  headers: {
    Accept: "text/event-stream",
    "Content-Type": "application/json",
  },
  body: JSON.stringify(generationRequest),
});

if (!response.ok) {
  throw new Error(await response.text());
}
if (!response.body) {
  throw new Error("Streaming responses are unavailable.");
}

const reader = response.body.getReader();
const decoder = new TextDecoder();
let buffer = "";
let terminalReceived = false;

while (!terminalReceived) {
  const { value, done } = await reader.read();
  buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });

  const frames = buffer.split(/\r?\n\r?\n/);
  buffer = frames.pop() ?? "";

  for (const frame of frames) {
    if (!frame || frame.startsWith(":")) continue;

    const data = frame
      .split(/\r?\n/)
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n");

    if (!data) continue;

    const generationEvent = JSON.parse(data);
    console.log(generationEvent.event, generationEvent.payload);

    terminalReceived =
      generationEvent.event === "completed" ||
      generationEvent.event === "error";
  }

  if (done) break;
}

await reader.cancel();
```

An `AbortController` can close the browser's local connection:

```javascript
const controller = new AbortController();

fetch(url, {
  method: "POST",
  signal: controller.signal,
  headers,
  body,
});

controller.abort();
```

Aborting delivery does not cancel generation on the server.

## Access from another machine

1. Replace `127.0.0.1` with the server hostname or IP and use published port
   `8001`.
2. Permit that port through the firewall, or expose it through an HTTPS reverse
   proxy.
3. Add the browser application's exact origin to the comma-separated
   `CORS_ORIGINS` environment variable.
4. Disable reverse-proxy response buffering and configure a response timeout
   longer than the maximum generation duration.
5. Keep the connection path free from intermediary compression or buffering
   that delays individual SSE frames.

The API currently has no endpoint authentication. Do not expose it directly to
the public internet without an authenticated gateway or equivalent protection.

Reconnecting with the same request starts a new generation job; `Last-Event-ID`
and historical replay are not supported.

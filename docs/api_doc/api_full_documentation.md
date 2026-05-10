# House Plan Generator (FPG) Server API Documentation

This document provides a comprehensive guide to the House Plan Generator (FPG) API. It is designed to be highly detailed, enabling both developers and AI agents to build or update client applications that communicate with this server.

---

## 1. Overview & Architecture

The FPG Server uses an **Asynchronous Job-Based Architecture**. Generating complex floor plans can be computationally intensive and may take several seconds to minutes. To prevent blocking the client, the server handles requests in the following sequence:

1.  **Job Submission**: The client submits a request to start a task (e.g., layout generation).
2.  **Immediate Response**: The server returns a `job_id` and a `202 Accepted` status.
3.  **Processing**: The server processes the job in a background worker.
4.  **Tracking**: The client can monitor the job's progress via Server-Sent Events (SSE) or by polling the status endpoint.
5.  **Retrieval**: Once the job status reaches `COMPLETED`, the final result (data and/or scores) is available.

---

## 2. Base URL & Authentication

- **Base URL**: `http://<server-address>:<port>` (e.g., `http://localhost:8000`)
- **Client Identification**: The server uses a mandatory header `X-Client-Id` to track jobs and sessions per client.
  - **Header**: `X-Client-Id: <unique-client-identifier>` (e.g., a UUID or user-specific string)
  - **Note**: If this header is missing, the server falls back to the client's IP address, but using a persistent ID is highly recommended for stability.

---

## 3. Job Lifecycle States

A job can be in one of the following states:

- `SEARCHING`: The algorithm is currently running and attempting to find a layout.
- `COMPLETED`: The job finished successfully (or found the best possible candidate before timing out).
- `TERMINATED`: The job was manually cancelled by the client.
- `timed_out`: The job exceeded the server-side timeout limit.

---

## 4. API Endpoints

### 4.1. Layout Generation (v2)

Submits a job to generate a floor plan based on room templates and dimensions.

- **URL**: `/algorithms/format/v2`
- **Method**: `POST`
- **Headers**: `X-Client-Id` (Required)
- **Request Body**: `FormatterV2ApiRequest`

| Field                | Type              | Description                                                              |
| :------------------- | :---------------- | :----------------------------------------------------------------------- |
| `floor_width`        | `float`           | Width of the building area (in cm).                                      |
| `floor_height`       | `float`           | Height of the building area (in cm).                                     |
| `aspect_ratio`       | `float \| string` | H/W ratio (e.g., `1.5` or `"3:2"`). Must be between `0.5` and `2.0`.     |
| `room_template`      | `object`          | The template containing room requirements.                               |
| `should_optuna_run`  | `boolean`         | (Optional) If `true`, runs an optimization search (defaults to `false`). |
| `optuna_trial_count` | `int`             | (Optional) Number of trials for optimization (defaults to `20`).         |

**`room_template` Structure**:

```json
{
  "name": "My House Template",
  "data": [
    { "type": "Living Room", "size": "Large", "name": "Main Lounge" },
    { "type": "Kitchen", "size": "Medium" },
    { "type": "Bedroom", "size": "Small", "name": "Guest Room" }
  ]
}
```

_Note: `type` and `size` are mandatory for each room._

**Response** (`202 Accepted`):

```json
{
  "job_id": "uuid-string",
  "status": "SEARCHING",
  "message": "Job accepted for processing."
}
```

---

### 4.2. Buildable Space Calculation

Submits a job to calculate the buildable area of a plot.

- **URL**: `/algorithms/buildable-space`
- **Method**: `POST`
- **Headers**: `X-Client-Id` (Required)
- **Request Body**: `BuildableSpaceRequest`

| Field                 | Type    | Description                                              |
| :-------------------- | :------ | :------------------------------------------------------- |
| `area`                | `float` | Total plot area.                                         |
| `segmentsCoordinates` | `list`  | List of `{x, y}` coordinates defining the plot boundary. |
| `roadConnected`       | `list`  | (Optional) List of segments connected to roads.          |
| `min_width`           | `float` | (Optional) Minimum width constraint.                     |
| `min_height`          | `float` | (Optional) Minimum height constraint.                    |

**`roadConnected` Item Structure**:

```json
{
  "segment": [
    { "x": 0, "y": 0 },
    { "x": 10, "y": 0 }
  ],
  "roadType": "Main Road"
}
```

**Response** (`202 Accepted`):

```json
{
  "job_id": "uuid-string",
  "status": "SEARCHING",
  "message": "Job accepted for processing."
}
```

---

### 4.3. Job Status & Result

Retrieves the current state and result of a specific job.

- **URL**: `/algorithms/job/{job_id}`
- **Method**: `GET`
- **Response**: `JobStateResponse`

| Field                | Type             | Description                                                 |
| :------------------- | :--------------- | :---------------------------------------------------------- |
| `job_id`             | `string`         | Unique identifier.                                          |
| `status`             | `string`         | Current status (`SEARCHING`, `COMPLETED`, etc.).            |
| `result`             | `object \| null` | The final payload (only populated when status is terminal). |
| `events`             | `list`           | History of progress events.                                 |
| `current_best_score` | `float \| null`  | Current highest score found (if applicable).                |

---

### 4.4. Event Stream (SSE)

Real-time updates via Server-Sent Events.

- **URL**: `/algorithms/job/{job_id}/events`
- **Method**: `GET`
- **Headers**: `Accept: text/event-stream`
- **Event Format**:

```text
id: 1
event: initiate_fpg
data: {"id": 1, "event": "initiate_fpg", "message": "...", "timestamp": "...", "data": {...}}
```

---

### 4.5. Cancel Job

- **URL**: `/algorithms/cancel`
- **Method**: `POST`
- **Body**: `{ "job_id": "optional-uuid" }`
- _Note: If `job_id` is omitted, the active job for the `X-Client-Id` is cancelled._

---

## 5. Detailed Data Structures

### 5.1. Job Result Payload (`result` field)

When a `FORMAT_V2` job completes, the `result` object contains:

```json
{
  "status": "FEASIBLE",
  "message": "Solver found a layout",
  "score": 85.5,
  "union_results": {
    "floor_plan_with_openings": {
      "floor_plan": [
        {
          "type": "Living Room",
          "name": "Main Lounge",
          "area": 25.4,
          "vertices": [
            [0, 0],
            [5, 0],
            [5, 5],
            [0, 5]
          ]
        }
      ],
      "openings": [
        {
          "room_name": "Main Lounge",
          "opening_type": "Window",
          "side": "north",
          "x1": 1.0,
          "y1": 5.0,
          "x2": 3.0,
          "y2": 5.0,
          "connected_room_name": "Outdoor"
        }
      ]
    },
    "unified_floor_plan": {
      "walls": [{ "x1": 0, "y1": 0, "x2": 5, "y2": 0 }],
      "total_wall_length": 20.0
    }
  }
}
```

### 5.2. `ProcessedRoomData` (Item in `floor_plan`)

| Field      | Type                | Description                                       |
| :--------- | :------------------ | :------------------------------------------------ |
| `type`     | `string`            | The room type.                                    |
| `name`     | `string`            | The unique name given to the room.                |
| `area`     | `float`             | Calculated area.                                  |
| `vertices` | `list[list[float]]` | List of `[x, y]` pairs defining the room polygon. |

### 5.3. `OpeningData` (Item in `openings`)

| Field                  | Type     | Description                                                   |
| :--------------------- | :------- | :------------------------------------------------------------ |
| `room_name`            | `string` | Name of the room containing the opening.                      |
| `opening_type`         | `string` | Type (e.g., `Door`, `Window`, `Entrance`).                    |
| `side`                 | `string` | Side relative to the room (`north`, `south`, `east`, `west`). |
| `x1`, `y1`, `x2`, `y2` | `float`  | Coordinates of the opening's start and end points.            |
| `connected_room_name`  | `string` | Name of the room on the other side of the opening.            |

### 5.4. `WallSegmentPayload` (Item in `walls`)

| Field      | Type    | Description                      |
| :--------- | :------ | :------------------------------- |
| `x1`, `y1` | `float` | Start point of the wall segment. |
| `x2`, `y2` | `float` | End point of the wall segment.   |

---

## 6. Common Progress Events

These events are sent via SSE or found in the `events` list:

- `JOB_STARTED`: Job accepted by the worker.
- `initiate_fpg`: Optimization trial started.
- `fpg_generated`: A draft layout was produced.
- `refine_1`, `refine_2`, `refine_3`: Post-generation refinement passes.
- `post_processed`: Geometric cleanup complete.
- `fpg_score`: Scoring results are ready.
- `current_best_updated`: A new highest-scoring layout was found (contains `result` in data).
- `success`: Job finished with a valid result.
- `time_out` / `fpg_low_score`: Termination events with explanation.

---

## 7. Error Handling

Errors follow a standard format:

```json
{
  "detail": "Detailed error message explaining what went wrong."
}
```

**Common HTTP Status Codes**:

- `202 Accepted`: Job submitted successfully.
- `404 Not Found`: Job ID or active job not found.
- `409 Conflict`: A job is already running for this `X-Client-Id`.
- `422 Unprocessable Entity`: Validation error (e.g., invalid aspect ratio).
- `500 Internal Server Error`: An unexpected system error occurred.

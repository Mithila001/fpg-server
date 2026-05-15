# House Plan Generator API Documentation - `/algorithms/format/v2`

This document describes how a client should interface with the `/algorithms/format/v2` endpoint to generate a house floor plan based on specific room requirements and floor dimensions.

## Endpoint Information

- **URL:** `/algorithms/format/v2`
- **Method:** `POST`
- **Status Codes:**
  - `202 Accepted`: Job submitted successfully.
  - `409 Conflict`: A job is already running for this client.
  - `422 Unprocessable Entity`: Validation error in the request body.

## Request Headers

| Header         | Type     | Required | Description                                                                                                                                                                         |
| :------------- | :------- | :------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `X-Client-ID`  | `string` | No       | A unique identifier for the client. Used to track active jobs and prevent concurrent executions by the same client. If not provided, the client's IP address is used as a fallback. |
| `Content-Type` | `string` | Yes      | Must be `application/json`.                                                                                                                                                         |

## Request Body

The request body must be a JSON object with the following structure:

### Root Fields

| Field                | Type                 | Required | Description                                                                                                                                        |
| :------------------- | :------------------- | :------- | :------------------------------------------------------------------------------------------------------------------------------------------------- |
| `floor_width`        | `number` (float)     | Yes      | The width of the available floor space in centimeters.                                                                                             |
| `floor_height`       | `number` (float)     | Yes      | The height of the available floor space in centimeters.                                                                                            |
| `aspect_ratio`       | `number` or `string` | Yes      | The desired height-to-width ratio of the house. Can be a float (e.g., `1.5`) or a string in "H:W" format (e.g., `3:2`). Valid range: `[0.5, 2.0]`. |
| `room_template`      | `object`             | Yes      | An object containing the room configuration template.                                                                                              |
| `should_optuna_run`  | `boolean`            | No       | If `true`, the server will run an optimization process (Optuna) to find a better layout. Default: `false`.                                         |
| `optuna_trial_count` | `integer`            | No       | The number of optimization trials to run if `should_optuna_run` is `true`. Default: `20`.                                                          |

### `room_template` Object

| Field  | Type            | Required | Description                           |
| :----- | :-------------- | :------- | :------------------------------------ |
| `name` | `string`        | Yes      | A descriptive name for the template.  |
| `data` | `array[object]` | Yes      | A list of room configuration objects. |

### Room Configuration Object (inside `data` array)

| Field  | Type     | Required | Description                                                                                            |
| :----- | :------- | :------- | :----------------------------------------------------------------------------------------------------- |
| `type` | `string` | Yes      | The type of the room. See [Supported Room Types](#supported-room-types).                               |
| `size` | `string` | Yes      | The size category for the room. Valid values: `small`, `regular`, `large`.                             |
| `id`   | `string` | No       | A unique identifier for this specific room instance (useful if multiple rooms of the same type exist). |
| `name` | `string` | No       | A human-readable name for the room.                                                                    |

#### Supported Room Types

- `livingRoom`
- `bedroom`
- `kitchen`
- `bathroom`
- `diningRoom` (Optional)
- `garage` (Optional)
- `veranda`
- `attachedBathroom` (Optional)

> [!IMPORTANT]
> The following room types are **mandatory** and must be present in the `data` list at least once:
> `bedroom`, `kitchen`, `bathroom`, `veranda`.
> Note: `livingRoom` is typically is not expected by the system due to it being add by the server by default for every floor plan.

## Example Request

```json
{
  "floor_width": 1200,
  "floor_height": 1800,
  "aspect_ratio": "3:2",
  "should_optuna_run": true,
  "optuna_trial_count": 10,
  "room_template": {
    "name": "Standard 2-Bedroom Plan",
    "data": [
      { "id": "living1", "type": "livingRoom", "size": "large", "name": "Main Hall" },
      { "id": "bed_1", "type": "bedroom", "size": "regular" },
      { "id": "bed_2", "type": "bedroom", "size": "small" },
      { "id": "kit_1", "type": "kitchen", "size": "regular" },
      { "id": "bath_1", "type": "bathroom", "size": "small" },
      { "id": "ver_1", "type": "veranda", "size": "small" },
      { "id": "gar_1", "type": "garage", "size": "regular" }
    ]
  }
}
```

---

## Response Structure

### Initial Submission Response (`202 Accepted`)

When the job is accepted, the server returns a `job_id`.

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "SEARCHING",
  "message": "Job accepted for processing."
}
```

### Monitoring Job Progress

Since floor plan generation is an intensive task, the API works asynchronously. After receiving a `job_id`, the client can monitor progress in two ways:

#### 1. Server-Sent Events (SSE) - Recommended

**URL:** `/algorithms/job/{job_id}/events`

The client can open an SSE connection to receive real-time updates. The server will emit events such as `JOB_STARTED`, `fpg_generated`, `refine_1`, `fpg_score`, and finally `COMPLETED`.

#### 2. Polling

**URL:** `/algorithms/job/{job_id}`

Clients can perform GET requests to this endpoint to check the current state of the job.

### Job Statuses

| Status       | Description                                                                  |
| :----------- | :--------------------------------------------------------------------------- |
| `SEARCHING`  | The job is currently being processed by the solver.                          |
| `COMPLETED`  | The job finished successfully (or reached a timeout with a valid candidate). |
| `TERMINATED` | The job was manually cancelled via the `/cancel` endpoint.                   |
| `timed_out`  | The job exceeded the maximum allowed time and was stopped without a result.  |

---

### Job Results (via `/algorithms/job/{job_id}`)

Once the job status becomes `COMPLETED`, the `result` field will contain the generated floor plan.

#### Success Response Example

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "result": {
    "status": "COMPLETED",
    "message": "Solver found a layout",
    "score": 92.5,
    "union_results": {
      "floor_plan_with_openings": {
        "floor_plan": [
          {
            "type": "livingRoom",
            "name": "livingRoom_1",
            "vertices": [[0, 0], [400, 0], [400, 500], [0, 500]],
            "area": 200000
          },
          ...
        ],
        "openings": [
          {
            "opening_type": "door",
            "x1": 400, "y1": 100, "x2": 400, "y2": 190,
            "room_name": "livingRoom_1",
            "connected_room_name": "hallway_1"
          },
          ...
        ]
      },
      "unified_floor_plan": {
        "walls": [
          { "x1": 0, "y1": 0, "x2": 400, "y2": 0 },
          ...
        ],
        "total_wall_length": 4500.5
      }
    }
  }
}
```

#### Field Explanations in Result

- **`score`**: A value from 0-100 indicating the quality of the generated plan based on internal heuristics (coverage, rectangularity, etc.).
- **`floor_plan`**: A list of rooms with their final coordinates (`vertices`) and calculated `area`.
- **`openings`**: A list of doors and windows placed in the layout.
- **`unified_floor_plan`**: A merged wall network. This is the most useful data for rendering the structural walls of the house without duplicate overlapping segments.
  - `walls`: Individual line segments representing the entire structural shell and internal partitions.
  - `total_wall_length`: Sum of all wall segment lengths (useful for cost estimation).

#### Failure Response Example

If the solver cannot find a valid layout within the constraints:

```json
{
  "status": "NO_FLOOR_PLAN",
  "message": "No floor plan found.",
  "reason": "time_out",
  "details": "Job exceeded timeout of 120s"
}
```

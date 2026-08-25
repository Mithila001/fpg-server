from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, TypeGuard
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

TERMINAL_STATES = {"completed", "failed", "cancelled", "timed_out"}
SSE_EVENT_TYPES = {
    "job",
    "stage",
    "candidate",
    "floor_plan",
    "attempt_error",
    "terminal",
}
COMPLETED_CLASSIFICATIONS = {"presentable", "usable"}
COMPLETED_OUTCOMES = {"presentable_plan_found", "best_usable_plan_returned"}


class FlowRequestError(RuntimeError):
    def __init__(self, method: str, url: str, status: int, body: Any) -> None:
        super().__init__(f"{method} {url} returned HTTP {status}")
        self.method = method
        self.url = url
        self.status = status
        self.body = body


class FlowValidationError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def announce(message: str) -> None:
    print(f"[{datetime.now().astimezone():%H:%M:%S}] {message}", flush=True)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def decode_json(raw: bytes) -> Any:
    if not raw:
        return None
    text = raw.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw_text": text}


def request_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    *,
    timeout: float = 30.0,
) -> tuple[int, dict[str, str], Any]:
    body = (
        json.dumps(payload, ensure_ascii=False).encode("utf-8")
        if payload is not None
        else None
    )
    request = Request(
        url,
        data=body,
        method=method,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "fpg-full-flow-runner/2.0",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return (
                response.status,
                dict(response.headers.items()),
                decode_json(response.read()),
            )
    except HTTPError as exc:
        response_body = decode_json(exc.read())
        raise FlowRequestError(method, url, exc.code, response_body) from exc


def write_output(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.p{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def require(condition: object, message: str) -> None:
    if not condition:
        raise FlowValidationError(message)


def require_object(value: Any, message: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FlowValidationError(message)
    return value


def require_list(value: Any, message: str) -> list[Any]:
    if not isinstance(value, list):
        raise FlowValidationError(message)
    return value


def require_string(value: Any, message: str) -> str:
    if not isinstance(value, str):
        raise FlowValidationError(message)
    return value


def require_non_empty_string(value: Any, message: str) -> str:
    if not isinstance(value, str) or not value:
        raise FlowValidationError(message)
    return value


def require_positive_int(value: Any, message: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise FlowValidationError(message)
    return value


def require_number(value: Any, message: str) -> int | float:
    if not is_number(value):
        raise FlowValidationError(message)
    return value


def is_number(value: object) -> TypeGuard[int | float]:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def header_value(headers: dict[str, str], name: str) -> str | None:
    expected = name.lower()
    for key, value in headers.items():
        if key.lower() == expected:
            return value
    return None


def run_validation(
    report: dict[str, Any],
    output_path: Path,
    name: str,
    validator: Callable[[], dict[str, Any] | None],
) -> None:
    try:
        details = validator() or {}
    except Exception as exc:
        report["validations"].append(
            {
                "name": name,
                "status": "failed",
                "message": str(exc),
            }
        )
        write_output(output_path, report)
        raise

    report["validations"].append(
        {
            "name": name,
            "status": "passed",
            "details": details,
        }
    )
    write_output(output_path, report)
    announce(f"Validation passed: {name}")


def validate_metadata(
    metadata: Any,
    floor_plan_job: dict[str, Any],
    expectations: dict[str, Any],
) -> dict[str, Any]:
    metadata_obj = require_object(metadata, "Metadata response must be a JSON object")

    expected_schema = expectations.get("metadata_schema_version", 2)
    require(
        metadata_obj.get("schema_version") == expected_schema,
        f"Expected metadata schema_version={expected_schema}",
    )

    expected_units = expectations.get("project_units_per_meter", 10)
    require(
        metadata_obj.get("project_units_per_meter") == expected_units,
        f"Expected project_units_per_meter={expected_units}",
    )

    requirements = require_list(
        metadata_obj.get("room_requirements"),
        "metadata.room_requirements must be a list",
    )
    sizes = require_list(
        metadata_obj.get("room_sizes"),
        "metadata.room_sizes must be a list",
    )
    ratios = require_list(
        metadata_obj.get("compatible_aspect_ratios"),
        "metadata.compatible_aspect_ratios must be a list",
    )

    requirement_by_type: dict[str, dict[str, Any]] = {}
    for raw_item in requirements:
        item = require_object(raw_item, "Every room requirement must be an object")
        room_type = require_non_empty_string(
            item.get("room_type"),
            "room_requirements.room_type must be a non-empty string",
        )
        requirement_by_type[room_type] = item

    supported_sizes: set[tuple[str, str]] = set()
    for raw_item in sizes:
        item = require_object(
            raw_item, "Every room size metadata entry must be an object"
        )
        room_type = require_non_empty_string(
            item.get("room_type"),
            "room_sizes.room_type must be a non-empty string",
        )
        size = require_non_empty_string(
            item.get("size"),
            "room_sizes.size must be a non-empty string",
        )
        supported_sizes.add((room_type, size))

    requested_rooms = require_list(
        floor_plan_job.get("rooms"),
        "floor_plan_job.rooms must be a list",
    )
    for raw_room in requested_rooms:
        room = require_object(raw_room, "Each requested room must be an object")
        room_type = require_non_empty_string(
            room.get("room_type"),
            "Requested room_type must be a non-empty string",
        )
        requirement = requirement_by_type.get(room_type)
        if requirement is None:
            raise FlowValidationError(
                f"Metadata does not expose requested room type {room_type!r}"
            )
        require(
            requirement.get("client_selectable") is True,
            f"Requested room type {room_type!r} is not client-selectable",
        )
        requested_size = room.get("requested_size")
        if requested_size is not None:
            requested_size_value = require_non_empty_string(
                requested_size,
                f"requested_size for {room_type!r} must be a non-empty string",
            )
            require(
                (room_type, requested_size_value) in supported_sizes,
                f"Metadata does not expose requested size {requested_size_value!r} for {room_type!r}",
            )

    aspect_ratio = floor_plan_job.get("aspect_ratio")
    if isinstance(aspect_ratio, str) and ":" in aspect_ratio:
        supported_labels: set[str] = set()
        for raw_item in ratios:
            item = require_object(
                raw_item, "Every aspect-ratio metadata entry must be an object"
            )
            label = item.get("label")
            if isinstance(label, str):
                supported_labels.add(label)
        require(
            aspect_ratio in supported_labels,
            f"Requested aspect ratio label {aspect_ratio!r} is not exposed by metadata",
        )

    return {
        "schema_version": metadata_obj.get("schema_version"),
        "project_units_per_meter": metadata_obj.get("project_units_per_meter"),
        "requested_room_count": len(requested_rooms),
    }


def validate_buildable_space(headers: dict[str, str], body: Any) -> dict[str, Any]:
    body_obj = require_object(body, "Buildable-space response must be an object")
    flow_id = require_non_empty_string(
        body_obj.get("flow_id"),
        "Buildable-space response must contain flow_id",
    )
    require(
        header_value(headers, "X-Flow-ID") == flow_id,
        "X-Flow-ID header must match body.flow_id",
    )

    buildable_land = require_object(
        body_obj.get("buildable_land"),
        "buildable_land must be an object",
    )
    usable_land = require_object(
        body_obj.get("usable_land"),
        "usable_land must be an object",
    )

    buildable_area = require_number(
        buildable_land.get("area"),
        "buildable_land.area must be numeric",
    )
    require(buildable_area > 0, "buildable_land.area must be positive")

    usable_width = require_positive_int(
        usable_land.get("width"),
        "usable_land.width must be a positive integer",
    )
    usable_length = require_positive_int(
        usable_land.get("length"),
        "usable_land.length must be a positive integer",
    )
    usable_area = require_positive_int(
        usable_land.get("area"),
        "usable_land.area must be a positive integer",
    )

    return {
        "flow_id": flow_id,
        "buildable_area": buildable_area,
        "usable_width": usable_width,
        "usable_length": usable_length,
        "usable_area": usable_area,
    }


def validate_job_created(created: Any) -> dict[str, Any]:
    created_obj = require_object(created, "Job creation response must be an object")
    job_id = require_non_empty_string(
        created_obj.get("job_id"),
        "Job creation response must contain job_id",
    )
    require(
        created_obj.get("state") == "queued",
        "New floor-plan job must start in queued state",
    )

    for field in ("status_url", "events_url", "cancellation_url"):
        value = require_non_empty_string(
            created_obj.get(field),
            f"Job creation response must contain {field}",
        )
        require(job_id in value, f"{field} must reference the created job_id")

    return {"job_id": job_id, "state": created_obj["state"]}


def event_summary(event: dict[str, Any]) -> str:
    sequence = event.get("sequence", "?")
    event_type = event.get("event_type", "unknown")
    stage = event.get("stage", "unknown")
    state = event.get("state", "unknown")
    message = event.get("message", "")
    trial = event.get("trial_number")
    candidate = event.get("candidate_id")
    data = event.get("data")
    suffix: list[str] = []
    if trial is not None:
        suffix.append(f"trial={trial}")
    if candidate is not None:
        suffix.append(f"candidate={candidate}")
    if isinstance(data, dict) and data.get("score") is not None:
        suffix.append(f"score={data['score']}")
    context = f" ({', '.join(suffix)})" if suffix else ""
    return f"SSE #{sequence} {event_type}: {stage}/{state} - {message}{context}"


def validate_sse_event(
    event: dict[str, Any],
    *,
    job_id: str,
    current_id: int | None,
    current_type: str | None,
    last_sequence: int,
) -> int:
    require(
        event.get("schema_version") == "1.0", "SSE event schema_version must be '1.0'"
    )
    require(
        event.get("job_id") == job_id, "SSE event job_id does not match created job"
    )

    sequence = require_positive_int(
        event.get("sequence"),
        "SSE sequence must be a positive integer",
    )
    require(
        sequence > last_sequence,
        "New SSE events must have strictly increasing sequence values",
    )
    if current_id is not None:
        require(sequence == current_id, "SSE id must equal data.sequence")

    event_type = require_non_empty_string(
        event.get("event_type"),
        "SSE event_type must be a non-empty string",
    )
    require(event_type in SSE_EVENT_TYPES, f"Unsupported SSE event_type {event_type!r}")
    if current_type is not None:
        require(
            event_type == current_type, "SSE event field must match data.event_type"
        )

    require_string(event.get("stage"), "SSE stage must be a string")
    require_string(event.get("state"), "SSE state must be a string")
    require_string(event.get("message"), "SSE message must be a string")
    require_object(event.get("data"), "SSE data must be an object")
    error = event.get("error")
    require(
        error is None or isinstance(error, dict), "SSE error must be null or an object"
    )

    return sequence


def consume_events(
    url: str,
    job_id: str,
    report: dict[str, Any],
    output_path: Path,
) -> dict[str, Any] | None:
    last_sequence = 0
    terminal: dict[str, Any] | None = None
    reconnect_count = 0

    while terminal is None:
        headers = {
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
            "User-Agent": "fpg-full-flow-runner/2.0",
        }
        if last_sequence:
            headers["Last-Event-ID"] = str(last_sequence)
        request = Request(url, method="GET", headers=headers)
        announce(
            "Connecting to SSE stream"
            + (f" after event {last_sequence}" if last_sequence else "")
        )
        try:
            with urlopen(request, timeout=180.0) as response:
                current_id: int | None = None
                current_type: str | None = None
                data_lines: list[str] = []

                while True:
                    raw_line = response.readline()
                    if not raw_line:
                        break
                    line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")

                    if line.startswith(":"):
                        announce("SSE heartbeat - job is still running")
                        continue
                    if line.startswith("id:"):
                        current_id = int(line[3:].strip())
                        continue
                    if line.startswith("event:"):
                        current_type = line[6:].strip()
                        continue
                    if line.startswith("data:"):
                        data_lines.append(line[5:].lstrip())
                        continue
                    if line != "" or not data_lines:
                        continue

                    event = json.loads("\n".join(data_lines))
                    if not isinstance(event, dict):
                        raise FlowValidationError("SSE data must contain a JSON object")

                    raw_sequence = event.get("sequence")
                    if not isinstance(raw_sequence, int) or isinstance(
                        raw_sequence, bool
                    ):
                        raise FlowValidationError("SSE sequence must be an integer")
                    sequence = raw_sequence
                    if sequence > last_sequence:
                        sequence = validate_sse_event(
                            event,
                            job_id=job_id,
                            current_id=current_id,
                            current_type=current_type,
                            last_sequence=last_sequence,
                        )
                        last_sequence = sequence
                        report["sse_events"].append(event)
                        report["last_event_id"] = last_sequence
                        announce(event_summary(event))
                        write_output(output_path, report)

                    if (
                        current_type == "terminal"
                        or event.get("event_type") == "terminal"
                    ):
                        terminal = event
                        break

                    current_id = None
                    current_type = None
                    data_lines = []

        except HTTPError as exc:
            raise FlowRequestError(
                "GET", url, exc.code, decode_json(exc.read())
            ) from exc
        except (TimeoutError, URLError, ConnectionError, OSError) as exc:
            reconnect_count += 1
            report["sse_reconnects"] = reconnect_count
            report["last_stream_error"] = {
                "timestamp_utc": utc_now(),
                "type": type(exc).__name__,
                "message": str(exc),
            }
            write_output(output_path, report)
            announce(f"SSE connection interrupted: {exc}; reconnecting in 2 seconds")
            time.sleep(2.0)

        if terminal is None:
            reconnect_count += 1
            report["sse_reconnects"] = reconnect_count
            write_output(output_path, report)
            announce(
                "SSE stream closed before a terminal event; reconnecting in 1 second"
            )
            time.sleep(1.0)

    return terminal


def validate_completed_floor_plan(
    floor_plan: Any,
    expectations: dict[str, Any],
) -> dict[str, Any]:
    floor_plan_obj = require_object(
        floor_plan,
        "Completed result.floor_plan must be an object",
    )
    rooms = require_list(
        floor_plan_obj.get("rooms"),
        "Completed floor plan rooms must be a list",
    )
    if not rooms:
        raise FlowValidationError("Completed floor plan must contain rooms")
    openings = require_list(
        floor_plan_obj.get("openings"),
        "Completed floor plan openings must be a list",
    )

    room_ids: set[str] = set()
    room_types: dict[str, str] = {}
    for raw_room in rooms:
        room = require_object(raw_room, "Every floor-plan room must be an object")
        room_id = require_non_empty_string(
            room.get("id"),
            "Every room must have a non-empty id",
        )
        room_type = require_non_empty_string(
            room.get("room_type"),
            f"Room {room_id!r} must have room_type",
        )
        require(room_id not in room_ids, f"Duplicate final room id {room_id!r}")
        room_ids.add(room_id)
        room_types[room_id] = room_type

        if expectations.get("require_no_solver_placeholders", True):
            require(
                room.get("role") != "solver_placeholder",
                f"Terminal plan contains solver placeholder room {room_id!r}",
            )

    opening_ids: set[str] = set()
    door_graph: dict[str, set[str]] = {room_id: set() for room_id in room_ids}
    entrance_roots: set[str] = set()
    main_entrance_count = 0

    for raw_opening in openings:
        opening = require_object(raw_opening, "Every opening must be an object")
        opening_id = require_non_empty_string(
            opening.get("id"),
            "Every opening must have a non-empty id",
        )
        require(opening_id not in opening_ids, f"Duplicate opening id {opening_id!r}")
        opening_ids.add(opening_id)

        connected_raw = require_list(
            opening.get("connected_room_ids", []),
            f"Opening {opening_id!r} connected_room_ids must be a list",
        )
        connected: list[str] = []
        for raw_room_id in connected_raw:
            room_id = require_non_empty_string(
                raw_room_id,
                f"Opening {opening_id!r} connected_room_ids must contain strings",
            )
            require(
                room_id in room_ids,
                f"Opening {opening_id!r} references unknown room {room_id!r}",
            )
            connected.append(room_id)

        if opening.get("opening_type") != "door":
            continue

        unique_connected = list(dict.fromkeys(connected))
        for index, left in enumerate(unique_connected):
            for right in unique_connected[index + 1 :]:
                door_graph[left].add(right)
                door_graph[right].add(left)

        if opening.get("purpose") == "main_entrance":
            main_entrance_count += 1
            if not unique_connected:
                raise FlowValidationError(
                    f"Main entrance {opening_id!r} must connect to at least one room"
                )
            entrance_roots.update(unique_connected)

    if expectations.get("require_single_main_entrance", True):
        require(
            main_entrance_count == 1,
            "Completed plan must contain exactly one main entrance",
        )

    unreachable: set[str] = set()
    if expectations.get("require_connected_room_access", True):
        if not entrance_roots:
            raise FlowValidationError(
                "Cannot validate room access without a main-entrance room"
            )
        visited = set(entrance_roots)
        queue: deque[str] = deque(entrance_roots)
        while queue:
            room_id = queue.popleft()
            for neighbour in door_graph[room_id]:
                if neighbour not in visited:
                    visited.add(neighbour)
                    queue.append(neighbour)
        unreachable = room_ids - visited
        require(
            not unreachable,
            "Rooms are not reachable from the main entrance through selected doors: "
            + ", ".join(sorted(unreachable)),
        )

    return {
        "room_count": len(room_ids),
        "opening_count": len(opening_ids),
        "main_entrance_count": main_entrance_count,
        "hallway_count": sum(1 for value in room_types.values() if value == "hallway"),
        "unreachable_room_ids": sorted(unreachable),
    }


def validate_completed_result(
    final_job: Any,
    terminal_event: dict[str, Any] | None,
    expectations: dict[str, Any],
) -> dict[str, Any]:
    final_job_obj = require_object(final_job, "Final job response must be an object")
    state = require_non_empty_string(
        final_job_obj.get("state"),
        "Final job response must contain state",
    )
    require(state in TERMINAL_STATES, f"Final job state is not terminal: {state!r}")

    if terminal_event is not None:
        require(
            terminal_event.get("state") == state,
            "Terminal SSE state must match retained job state",
        )

    require(state == "completed", f"Expected completed job, received {state!r}")
    result = require_object(
        final_job_obj.get("result"),
        "Completed job must contain result",
    )
    require(
        final_job_obj.get("error") is None, "Completed job must not contain an error"
    )

    classification = require_non_empty_string(
        result.get("classification"),
        "Completed result must contain classification",
    )
    outcome = require_non_empty_string(
        result.get("outcome"),
        "Completed result must contain outcome",
    )
    require(
        classification in COMPLETED_CLASSIFICATIONS,
        f"Unexpected completed classification {classification!r}",
    )
    require(outcome in COMPLETED_OUTCOMES, f"Unexpected completed outcome {outcome!r}")

    scoring = require_object(
        result.get("scoring"),
        "Completed result must contain scoring",
    )
    total_score = require_number(
        scoring.get("total_score"),
        "scoring.total_score must be numeric",
    )
    require(
        0.0 <= float(total_score) <= 100.0, "scoring.total_score must be within 0..100"
    )

    minimum_score = require_number(
        expectations.get("minimum_completed_score", 80.0),
        "expectations.minimum_completed_score must be numeric",
    )
    require(
        float(total_score) >= float(minimum_score),
        f"Completed score {total_score} is below expected minimum {minimum_score}",
    )

    if expectations.get("require_critical_pass", True):
        require(
            scoring.get("passed_critical") is True,
            "Completed plan must pass critical scoring",
        )
        require(
            scoring.get("critical_failure") is None,
            "Critical-pass result must not contain critical_failure",
        )

    floor_plan_details = validate_completed_floor_plan(
        result.get("floor_plan"), expectations
    )
    return {
        "classification": classification,
        "outcome": outcome,
        "total_score": total_score,
        "passed_critical": scoring.get("passed_critical"),
        **floor_plan_details,
    }


def validate_completed_sse(
    events: list[dict[str, Any]],
    final_job: dict[str, Any],
    expectations: dict[str, Any],
) -> dict[str, Any]:
    if not events:
        raise FlowValidationError("Expected at least one SSE event")
    require(
        events[-1].get("event_type") == "terminal", "Last SSE event must be terminal"
    )

    required_stage_states_raw = expectations.get(
        "required_stage_states",
        [
            ["preprocessing", "completed"],
            ["candidate_search", "started"],
            ["candidate_circulation", "started"],
            ["initial_generation", "completed"],
            ["refinement_a", "completed"],
            ["refinement_b", "completed"],
            ["post_processing", "started"],
            ["openings", "started"],
            ["final_scoring", "completed"],
        ],
    )
    required_stage_states = require_list(
        required_stage_states_raw,
        "expectations.required_stage_states must be a list",
    )

    observed = {(event.get("stage"), event.get("state")) for event in events}
    missing: list[list[str]] = []
    for raw_item in required_stage_states:
        item = require_list(
            raw_item,
            "Each required_stage_states item must be [stage, state]",
        )
        if len(item) != 2:
            raise FlowValidationError(
                "Each required_stage_states item must contain exactly [stage, state]"
            )
        stage = require_string(
            item[0],
            "required_stage_states stage must be a string",
        )
        state = require_string(
            item[1],
            "required_stage_states state must be a string",
        )
        if (stage, state) not in observed:
            missing.append([stage, state])
    require(
        not missing, f"Missing required successful SSE stage/state events: {missing}"
    )

    candidate_score_events = [
        event
        for event in events
        if event.get("event_type") == "candidate"
        and event.get("stage") == "candidate_scoring"
    ]
    if not candidate_score_events:
        raise FlowValidationError("Expected candidate_scoring SSE events")

    for event in candidate_score_events:
        data = require_object(
            event.get("data"),
            "candidate_scoring data must be an object",
        )
        require_number(
            data.get("score"),
            "candidate_scoring event must contain numeric score",
        )
        require_number(
            data.get("threshold"),
            "candidate_scoring event must contain numeric threshold",
        )
        require(
            isinstance(data.get("accepted"), bool),
            "candidate_scoring event must contain boolean accepted",
        )
        require_non_empty_string(
            data.get("circulation_artifact"),
            "candidate_scoring event must contain circulation_artifact",
        )

    result = require_object(
        final_job.get("result"),
        "Final job result must be an object for SSE validation",
    )
    scoring = require_object(
        result.get("scoring"),
        "Final job result must contain scoring for SSE validation",
    )
    final_score = require_number(
        scoring.get("total_score"),
        "Final scoring.total_score must be numeric for SSE validation",
    )
    final_critical = scoring.get("passed_critical")
    if not isinstance(final_critical, bool):
        raise FlowValidationError(
            "Final scoring.passed_critical must be boolean for SSE validation"
        )

    final_scoring_events = [
        event
        for event in events
        if event.get("event_type") == "floor_plan"
        and event.get("stage") == "final_scoring"
        and event.get("state") == "completed"
    ]
    if not final_scoring_events:
        raise FlowValidationError(
            "Expected at least one completed final_scoring SSE event"
        )

    matching_score = False
    for event in final_scoring_events:
        data = event.get("data")
        if not isinstance(data, dict):
            continue
        event_score = data.get("score")
        if not is_number(event_score):
            continue
        if (
            abs(float(event_score) - float(final_score)) <= 1e-9
            and data.get("passed_critical") == final_critical
        ):
            matching_score = True
            break

    require(
        matching_score,
        "No completed final_scoring SSE event matches the retained terminal score",
    )

    return {
        "event_count": len(events),
        "candidate_score_event_count": len(candidate_score_events),
        "final_scoring_event_count": len(final_scoring_events),
        "last_sequence": events[-1].get("sequence"),
    }


def run(input_path: Path, output_path: Path) -> int:
    report: dict[str, Any] = {
        "schema_version": "2.0",
        "started_at_utc": utc_now(),
        "completed_at_utc": None,
        "status": "running",
        "input_file": str(input_path.resolve()),
        "output_file": str(output_path.resolve()),
        "steps": [],
        "validations": [],
        "sse_events": [],
        "sse_reconnects": 0,
        "last_event_id": 0,
        "terminal_event": None,
        "final_job": None,
        "errors": [],
    }
    write_output(output_path, report)

    try:
        input_data = read_json(input_path)
        base_url = str(input_data.get("base_url", "http://127.0.0.1:8000")).rstrip("/")
        expectations = require_object(
            input_data.get("expectations", {}),
            "input.json expectations must be an object",
        )

        generation_input = input_data.get("floor_plan_job")
        if not isinstance(generation_input, dict):
            raise ValueError("input.json floor_plan_job must be an object")

        announce(f"Starting full frontend-style flow against {base_url}")

        announce("Step 1/5: requesting frontend metadata")
        status, headers, body = request_json("GET", f"{base_url}/api/v1/metadata")
        report["steps"].append(
            {
                "name": "metadata",
                "status_code": status,
                "headers": headers,
                "body": body,
            }
        )
        write_output(output_path, report)
        announce(f"Metadata received (HTTP {status})")
        run_validation(
            report,
            output_path,
            "metadata_matches_generation_request",
            lambda: validate_metadata(body, generation_input, expectations),
        )

        buildable_input = input_data.get("buildable_space")
        if not isinstance(buildable_input, dict):
            raise ValueError("input.json buildable_space must be an object")
        announce("Step 2/5: calculating buildable and usable land")
        status, headers, body = request_json(
            "POST", f"{base_url}/api/v1/buildable-space", buildable_input
        )
        report["steps"].append(
            {
                "name": "buildable_space",
                "status_code": status,
                "headers": headers,
                "body": body,
            }
        )
        write_output(output_path, report)
        announce(f"Buildable-space result received (HTTP {status})")
        run_validation(
            report,
            output_path,
            "buildable_space_contract",
            lambda: validate_buildable_space(headers, body),
        )

        announce("Step 3/5: creating asynchronous floor-plan job")
        status, headers, created = request_json(
            "POST", f"{base_url}/api/v1/floor-plan-jobs", generation_input
        )
        report["steps"].append(
            {
                "name": "create_floor_plan_job",
                "status_code": status,
                "headers": headers,
                "body": created,
            }
        )
        write_output(output_path, report)
        run_validation(
            report,
            output_path,
            "job_creation_contract",
            lambda: validate_job_created(created),
        )
        created_obj = require_object(created, "Job creation response must be an object")
        job_id = require_non_empty_string(
            created_obj.get("job_id"),
            "Job creation response must contain job_id",
        )
        report["job_id"] = job_id
        write_output(output_path, report)
        announce(f"Floor-plan job created: {job_id} (HTTP {status})")

        events_url = require_non_empty_string(
            created_obj.get("events_url"),
            "Job creation response must contain events_url",
        )
        if not events_url.startswith("http"):
            events_url = base_url + events_url
        announce("Step 4/5: consuming live generation events")
        terminal = consume_events(events_url, job_id, report, output_path)
        report["terminal_event"] = terminal
        write_output(output_path, report)

        status_url = require_non_empty_string(
            created_obj.get("status_url"),
            "Job creation response must contain status_url",
        )
        if not status_url.startswith("http"):
            status_url = base_url + status_url
        announce("Step 5/5: fetching retained terminal status and full result")
        status, headers, final_job = request_json("GET", status_url)
        report["steps"].append(
            {
                "name": "final_job_status",
                "status_code": status,
                "headers": headers,
                "body": final_job,
            }
        )
        report["final_job"] = final_job
        write_output(output_path, report)

        run_validation(
            report,
            output_path,
            "completed_result_new_core_invariants",
            lambda: validate_completed_result(final_job, terminal, expectations),
        )
        final_job_obj = require_object(
            final_job,
            "Final job response must be an object",
        )
        sse_events_raw = require_list(
            report.get("sse_events"),
            "Internal report.sse_events must be a list",
        )
        sse_events: list[dict[str, Any]] = [
            require_object(event, "Internal SSE event report entry must be an object")
            for event in sse_events_raw
        ]
        run_validation(
            report,
            output_path,
            "completed_sse_pipeline_contract",
            lambda: validate_completed_sse(sse_events, final_job_obj, expectations),
        )

        report["status"] = "completed"
        report["completed_at_utc"] = utc_now()
        write_output(output_path, report)
        announce("Full flow and new fpg-core integration validations passed")
        announce(f"Complete report saved to {output_path.resolve()}")
        return 0

    except KeyboardInterrupt:
        report["status"] = "interrupted"
        report["completed_at_utc"] = utc_now()
        report["errors"].append(
            {
                "timestamp_utc": utc_now(),
                "type": "KeyboardInterrupt",
                "message": "Run interrupted by user",
            }
        )
        write_output(output_path, report)
        announce("Run interrupted; partial output was saved")
        return 130
    except BaseException as exc:
        error: dict[str, Any] = {
            "timestamp_utc": utc_now(),
            "type": type(exc).__name__,
            "message": str(exc),
        }
        if isinstance(exc, FlowRequestError):
            error.update(
                {
                    "method": exc.method,
                    "url": exc.url,
                    "status_code": exc.status,
                    "response_body": exc.body,
                }
            )
        report["status"] = "error"
        report["completed_at_utc"] = utc_now()
        report["errors"].append(error)
        write_output(output_path, report)
        announce(f"Flow failed: {type(exc).__name__}: {exc}")
        announce(f"Full error report saved to {output_path.resolve()}")
        return 1


def parse_args() -> argparse.Namespace:
    directory = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description=(
            "Run the complete frontend-style fpg-server API flow and validate the "
            "current fpg-core integration contracts."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=directory / "input.json",
        help="Input JSON path (default: test/input.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=directory / "output.json",
        help="Output JSON path (default: test/output.json)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    sys.exit(run(arguments.input, arguments.output))

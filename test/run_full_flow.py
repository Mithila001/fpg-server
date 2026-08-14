from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

TERMINAL_STATES = {"completed", "failed", "cancelled", "timed_out"}


class FlowRequestError(RuntimeError):
    def __init__(self, method: str, url: str, status: int, body: Any) -> None:
        super().__init__(f"{method} {url} returned HTTP {status}")
        self.method = method
        self.url = url
        self.status = status
        self.body = body


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
            "User-Agent": "fpg-full-flow-runner/1.0",
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


def consume_events(
    url: str,
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
            "User-Agent": "fpg-full-flow-runner/1.0",
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
                        raise ValueError("SSE data must contain a JSON object")
                    sequence = int(event.get("sequence", current_id or 0))
                    if sequence > last_sequence:
                        last_sequence = sequence
                        report["sse_events"].append(event)
                        report["last_event_id"] = last_sequence
                        announce(event_summary(event))
                        write_output(output_path, report)
                    if current_type == "terminal" or event.get("event_type") == "terminal":
                        terminal = event
                        break
                    current_id = None
                    current_type = None
                    data_lines = []

        except HTTPError as exc:
            raise FlowRequestError("GET", url, exc.code, decode_json(exc.read())) from exc
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
            announce("SSE stream closed before a terminal event; reconnecting in 1 second")
            time.sleep(1.0)

    return terminal


def run(input_path: Path, output_path: Path) -> int:
    report: dict[str, Any] = {
        "schema_version": "1.0",
        "started_at_utc": utc_now(),
        "completed_at_utc": None,
        "status": "running",
        "input_file": str(input_path.resolve()),
        "output_file": str(output_path.resolve()),
        "steps": [],
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
        announce(f"Starting full frontend-style flow against {base_url}")

        announce("Step 1/5: requesting frontend metadata")
        status, headers, body = request_json("GET", f"{base_url}/api/v1/metadata")
        report["steps"].append(
            {"name": "metadata", "status_code": status, "headers": headers, "body": body}
        )
        write_output(output_path, report)
        announce(f"Metadata received (HTTP {status})")

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

        generation_input = input_data.get("floor_plan_job")
        if not isinstance(generation_input, dict):
            raise ValueError("input.json floor_plan_job must be an object")
        announce("Step 3/5: creating asynchronous floor-plan job")
        status, headers, created = request_json(
            "POST", f"{base_url}/api/v1/floor-plan-jobs", generation_input
        )
        if not isinstance(created, dict) or not isinstance(created.get("job_id"), str):
            raise ValueError("Job creation response does not contain job_id")
        report["steps"].append(
            {
                "name": "create_floor_plan_job",
                "status_code": status,
                "headers": headers,
                "body": created,
            }
        )
        report["job_id"] = created["job_id"]
        write_output(output_path, report)
        announce(f"Floor-plan job created: {created['job_id']} (HTTP {status})")

        events_url = str(created["events_url"])
        if not events_url.startswith("http"):
            events_url = base_url + events_url
        announce("Step 4/5: consuming live generation events")
        terminal = consume_events(events_url, report, output_path)
        report["terminal_event"] = terminal
        write_output(output_path, report)

        status_url = str(created["status_url"])
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
        final_state = final_job.get("state") if isinstance(final_job, dict) else None
        report["status"] = "completed" if final_state in TERMINAL_STATES else "incomplete"
        report["completed_at_utc"] = utc_now()
        write_output(output_path, report)
        announce(f"Full flow finished with job state: {final_state}")
        announce(f"Complete report saved to {output_path.resolve()}")
        return 0 if final_state == "completed" else 1

    except KeyboardInterrupt:
        report["status"] = "interrupted"
        report["completed_at_utc"] = utc_now()
        report["errors"].append(
            {"timestamp_utc": utc_now(), "type": "KeyboardInterrupt", "message": "Run interrupted by user"}
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
        description="Run the complete frontend-style fpg-server API flow."
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

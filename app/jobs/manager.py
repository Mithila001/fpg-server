from __future__ import annotations

import asyncio
import json
import multiprocessing as mp
import os
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from queue import Empty
from typing import Any, AsyncIterator
from uuid import uuid4

from app.artifacts.serializers import to_json_value
from app.core_config import SERVER_CONFIG_PATH, ServerConfig
from app.pipeline.generation import GenerationPipelineRequest
from app.streaming import EventError, EventType, GenerationEvent, JobState, WorkerEvent
from app.util.jsonl_logging import JsonlLogWriter

from .worker import WorkerFinished, run_generation_worker


class QueueFullError(RuntimeError):
    pass


class JobNotFoundError(RuntimeError):
    pass


class JobNotCancellableError(RuntimeError):
    pass


class CancellationOutcome(StrEnum):
    REQUESTED = "cancellation_requested"
    ALREADY_REQUESTED = "already_requested"


@dataclass(slots=True)
class JobRecord:
    job_id: str
    state: JobState
    created_at: datetime
    flow_directory: Path
    request: GenerationPipelineRequest | None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    sequence: int = 0
    process: Any = None
    cancellation: Any = None
    updated: asyncio.Event = field(default_factory=asyncio.Event)

    @property
    def events_path(self) -> Path:
        return self.flow_directory / "json" / "events.jsonl"

    @property
    def snapshot_path(self) -> Path:
        return self.flow_directory / "json" / "job" / "snapshot.json"

    @property
    def result_path(self) -> Path:
        return self.flow_directory / "json" / "job" / "result.json"


class GenerationJobManager:
    def __init__(self, config: ServerConfig) -> None:
        self.config = config
        self._jobs: dict[str, JobRecord] = {}
        self._lock = asyncio.Lock()
        self._slots = asyncio.Semaphore(config.server.max_concurrent_jobs)
        self._tasks: set[asyncio.Task[None]] = set()
        self._context = mp.get_context("spawn")
        self._output_root = config.server.output_root.resolve()
        self._logs = JsonlLogWriter(self._output_root)

    async def start(self) -> None:
        self._output_root.mkdir(parents=True, exist_ok=True)
        await self._restore_retained_jobs()

    async def shutdown(self) -> None:
        for record in self._jobs.values():
            if not record.state.terminal and record.cancellation is not None:
                record.cancellation.set()
        if self._tasks:
            await asyncio.gather(*tuple(self._tasks), return_exceptions=True)

    async def create(self, request: GenerationPipelineRequest) -> JobRecord:
        async with self._lock:
            self._expire()
            active = sum(not job.state.terminal for job in self._jobs.values())
            if active >= (
                self.config.server.max_concurrent_jobs
                + self.config.server.max_queued_jobs
            ):
                raise QueueFullError("The generation queue is full.")

            job_id = str(uuid4())
            now = datetime.now(UTC)
            flow_name = f"{now:%Y%m%dT%H%M%S%fZ}_{job_id}"
            flow_directory = self._output_root / "flows" / flow_name
            (flow_directory / "json" / "job").mkdir(parents=True)
            (flow_directory / "json" / "candidate_circulation").mkdir()
            record = JobRecord(
                job_id=job_id,
                state=JobState.QUEUED,
                created_at=now,
                flow_directory=flow_directory,
                request=replace(
                    request,
                    job_id=job_id,
                    flow_directory=str(flow_directory),
                ),
            )
            self._jobs[job_id] = record
            self._append_event(
                record,
                WorkerEvent(
                    EventType.JOB,
                    "job",
                    JobState.QUEUED.value,
                    "Generation job queued",
                ),
            )
            self._write_snapshot(record)
            task = asyncio.create_task(self._dispatch(record))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
            return record

    async def get(self, job_id: str) -> JobRecord:
        async with self._lock:
            self._expire()
            record = self._jobs.get(job_id)
            if record is None:
                raise JobNotFoundError(job_id)
            return record

    async def cancel(self, job_id: str) -> CancellationOutcome:
        record = await self.get(job_id)
        if record.state is JobState.CANCELLATION_REQUESTED:
            return CancellationOutcome.ALREADY_REQUESTED
        if record.state.terminal:
            raise JobNotCancellableError(job_id)
        if record.state is JobState.QUEUED:
            await self._finalize(
                record,
                JobState.CANCELLED,
                error={
                    "stage": "job",
                    "code": "generation_cancelled",
                    "message": "Queued generation job was cancelled.",
                    "details": {},
                },
            )
            return CancellationOutcome.REQUESTED
        record.state = JobState.CANCELLATION_REQUESTED
        if record.cancellation is not None:
            record.cancellation.set()
        self._append_event(
            record,
            WorkerEvent(
                EventType.JOB,
                "job",
                JobState.CANCELLATION_REQUESTED.value,
                "Cancellation requested",
            ),
        )
        self._write_snapshot(record)
        return CancellationOutcome.REQUESTED

    async def events(
        self, job_id: str, after_sequence: int
    ) -> AsyncIterator[bytes]:
        record = await self.get(job_id)
        next_sequence = max(1, after_sequence + 1)
        while True:
            sent = False
            if record.events_path.exists():
                for line in record.events_path.read_text(encoding="utf-8").splitlines():
                    payload = json.loads(line)
                    sequence = int(payload["sequence"])
                    if sequence < next_sequence:
                        continue
                    event_type = str(payload["event_type"])
                    frame = (
                        f"id: {sequence}\n"
                        f"event: {event_type}\n"
                        f"data: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n\n"
                    )
                    yield frame.encode("utf-8")
                    next_sequence = sequence + 1
                    sent = True
            if record.state.terminal and next_sequence > record.sequence:
                return
            if sent:
                continue
            record.updated.clear()
            try:
                await asyncio.wait_for(
                    record.updated.wait(),
                    timeout=self.config.server.sse_heartbeat_seconds,
                )
            except TimeoutError:
                yield b": heartbeat\n\n"

    def public_snapshot(self, record: JobRecord) -> dict[str, Any]:
        return {
            "job_id": record.job_id,
            "state": record.state.value,
            "created_at": record.created_at.isoformat(),
            "started_at": record.started_at.isoformat() if record.started_at else None,
            "completed_at": (
                record.completed_at.isoformat() if record.completed_at else None
            ),
            "result": record.result,
            "error": record.error,
        }

    async def _dispatch(self, record: JobRecord) -> None:
        async with self._slots:
            if record.state.terminal:
                return
            request = record.request
            if request is None:
                return
            record.state = JobState.RUNNING
            record.started_at = datetime.now(UTC)
            queue = self._context.Queue()
            cancellation = self._context.Event()
            process = self._context.Process(
                target=run_generation_worker,
                args=(request, str(SERVER_CONFIG_PATH), queue, cancellation),
                daemon=True,
            )
            record.process = process
            record.cancellation = cancellation
            process.start()
            self._append_event(
                record,
                WorkerEvent(
                    EventType.JOB,
                    "job",
                    JobState.RUNNING.value,
                    "Generation job started",
                    {"timeout_seconds": self.config.server.request_timeout_seconds},
                ),
            )
            self._write_snapshot(record)
            await self._monitor(record, queue, process, cancellation)

    async def _monitor(
        self, record: JobRecord, queue: Any, process: Any, cancellation: Any
    ) -> None:
        loop = asyncio.get_running_loop()
        assert record.started_at is not None
        deadline = loop.time() + self.config.server.request_timeout_seconds
        grace_deadline: float | None = None
        forced_state: JobState | None = None
        finished: WorkerFinished | None = None

        while finished is None:
            if loop.time() >= deadline and forced_state is None:
                forced_state = JobState.TIMED_OUT
                cancellation.set()
                grace_deadline = loop.time() + self.config.server.cancellation_grace_seconds
            if record.state is JobState.CANCELLATION_REQUESTED and forced_state is None:
                forced_state = JobState.CANCELLED
                cancellation.set()
                grace_deadline = loop.time() + self.config.server.cancellation_grace_seconds
            if grace_deadline is not None and loop.time() >= grace_deadline:
                process.terminate()
                break
            try:
                if process.is_alive():
                    message = await asyncio.to_thread(queue.get, True, 0.25)
                else:
                    message = queue.get_nowait()
            except Empty:
                if process.is_alive():
                    continue
                break
            if isinstance(message, WorkerEvent):
                self._append_event(record, message)
            elif isinstance(message, WorkerFinished):
                finished = message

        await asyncio.to_thread(process.join, self.config.server.cancellation_grace_seconds)
        if process.is_alive():
            process.terminate()
            await asyncio.to_thread(process.join)

        if forced_state is not None:
            error = (
                finished.error
                if finished is not None and finished.error is not None
                else {
                    "stage": "generation",
                    "code": (
                        "generation_timed_out"
                        if forced_state is JobState.TIMED_OUT
                        else "generation_cancelled"
                    ),
                    "message": (
                        "The generation deadline was reached."
                        if forced_state is JobState.TIMED_OUT
                        else "Generation was cancelled."
                    ),
                    "details": {},
                }
            )
            result = None
            details = error.get("details") if isinstance(error, dict) else None
            if isinstance(details, dict) and "best_floor_plan" in details:
                result = {
                    "floor_plan": details["best_floor_plan"],
                    "scoring": details.get("best_scoring"),
                    "classification": "best_available",
                    "outcome": "deadline_reached",
                }
            await self._finalize(record, forced_state, result=result, error=error)
            return
        if finished is None:
            await self._finalize(
                record,
                JobState.FAILED,
                error={
                    "stage": "generation",
                    "code": "worker_exited",
                    "message": "Generation worker exited without a result.",
                    "details": {"exit_code": process.exitcode},
                },
            )
        elif finished.result is not None:
            await self._finalize(record, JobState.COMPLETED, result=finished.result)
        elif finished.termination_reason in {"timeout", "cancelled"}:
            terminal_state = (
                JobState.TIMED_OUT
                if finished.termination_reason == "timeout"
                else JobState.CANCELLED
            )
            error = finished.error or {}
            details = error.get("details")
            result = None
            if isinstance(details, dict) and "best_floor_plan" in details:
                result = {
                    "floor_plan": details["best_floor_plan"],
                    "scoring": details.get("best_scoring"),
                    "classification": "best_available",
                    "outcome": "deadline_reached",
                }
            await self._finalize(
                record, terminal_state, result=result, error=error
            )
        else:
            await self._finalize(
                record, JobState.FAILED, error=finished.error or {}
            )

    async def _finalize(
        self,
        record: JobRecord,
        state: JobState,
        *,
        result: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> None:
        if record.state.terminal:
            return
        record.state = state
        record.completed_at = datetime.now(UTC)
        record.result = result
        record.error = error
        event_error = None
        if error is not None:
            details = error.get("details")
            event_error = EventError(
                code=str(error.get("code", "generation_failed")),
                message=str(error.get("message", "Generation failed.")),
                recoverable=False,
                details=details if isinstance(details, dict) else {},
            )
        self._append_event(
            record,
            WorkerEvent(
                EventType.TERMINAL,
                "job",
                state.value,
                {
                    JobState.COMPLETED: "Generation completed",
                    JobState.CANCELLED: "Generation cancelled",
                    JobState.TIMED_OUT: "Generation timed out",
                }.get(state, "Generation failed"),
                {"result": result} if result is not None else {},
                event_error,
            ),
        )
        if result is not None or error is not None:
            self._write_result(record)
        if error is not None:
            assert record.completed_at is not None
            self._logs.error(
                {
                    "timestamp_utc": record.completed_at.isoformat(),
                    "stage": error.get("stage", "generation"),
                    "code": error.get("code", "generation_failed"),
                    "recoverable": False,
                    "job_id": record.job_id,
                    "message": error.get("message", "Generation failed."),
                    "details": error.get("details", {}),
                }
            )
        self._write_snapshot(record)

    def _append_event(self, record: JobRecord, event: WorkerEvent) -> None:
        record.sequence += 1
        envelope = GenerationEvent(
            job_id=record.job_id,
            sequence=record.sequence,
            event_type=event.event_type,
            stage=event.stage,
            state=event.state,
            message=event.message,
            data=event.data,
            error=event.error,
            trial_number=event.trial_number,
            candidate_id=event.candidate_id,
        )
        serialized = to_json_value(envelope)
        record.events_path.parent.mkdir(parents=True, exist_ok=True)
        with record.events_path.open("a", encoding="utf-8") as stream:
            stream.write(
                json.dumps(serialized, ensure_ascii=False, separators=(",", ":"))
                + "\n"
            )
            stream.flush()
            os.fsync(stream.fileno())
        record.updated.set()

    def _write_snapshot(self, record: JobRecord) -> None:
        payload = {
            **self.public_snapshot(record),
            "flow_directory": str(record.flow_directory),
            "sequence": record.sequence,
        }
        path = record.snapshot_path
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)

    def _write_result(self, record: JobRecord) -> None:
        path = record.result_path
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.write_text(
            json.dumps(
                {"state": record.state.value, "result": record.result, "error": record.error},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)

    async def _restore_retained_jobs(self) -> None:
        flows = self._output_root / "flows"
        if not flows.exists():
            return
        for path in flows.glob("*/json/job/snapshot.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                completed_raw = payload.get("completed_at")
                completed = (
                    datetime.fromisoformat(completed_raw)
                    if isinstance(completed_raw, str)
                    else None
                )
                state = JobState(payload["state"])
                record = JobRecord(
                    job_id=payload["job_id"],
                    state=state,
                    created_at=datetime.fromisoformat(payload["created_at"]),
                    started_at=(
                        datetime.fromisoformat(payload["started_at"])
                        if payload.get("started_at")
                        else None
                    ),
                    completed_at=completed,
                    flow_directory=Path(payload["flow_directory"]),
                    request=None,
                    result=payload.get("result"),
                    error=payload.get("error"),
                    sequence=int(payload.get("sequence", 0)),
                )
            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                continue
            self._jobs[record.job_id] = record
            if not record.state.terminal:
                await self._finalize(
                    record,
                    JobState.FAILED,
                    error={
                        "stage": "job",
                        "code": "server_restarted",
                        "message": "The server restarted while this job was active.",
                        "details": {},
                    },
                )
        self._expire()

    def _expire(self) -> None:
        now = datetime.now(UTC)
        expired = [
            job_id
            for job_id, record in self._jobs.items()
            if record.completed_at is not None
            and (now - record.completed_at).total_seconds()
            > self.config.server.job_retention_seconds
        ]
        for job_id in expired:
            del self._jobs[job_id]

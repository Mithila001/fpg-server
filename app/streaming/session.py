from __future__ import annotations

import asyncio
import json
from collections import deque
from concurrent.futures import Future
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import AsyncIterator

from fastapi import Request

from app.algorithms.candidate_search import CandidatePoint
from app.algorithms.types_new import FloorPlan
from app.artifacts.serializers import to_json_value

from .contracts import (
    CandidateTrialPayload,
    CompletedPayload,
    CompletionOutcome,
    ErrorPayload,
    FloorPlanClassification,
    FloorPlanPayload,
    GenerationEventPayload,
    GenerationStatus,
    ProgressPayload,
    StatusPayload,
    event_name,
)


@dataclass(frozen=True, slots=True)
class GenerationStreamSettings:
    candidate_trial_throttle_ms: int = 100
    progress_throttle_ms: int = 500
    queue_capacity: int = 64
    heartbeat_interval_seconds: float = 15.0

    def __post_init__(self) -> None:
        if self.candidate_trial_throttle_ms < 0:
            raise ValueError("candidate_trial_throttle_ms cannot be negative")
        if self.progress_throttle_ms < 0:
            raise ValueError("progress_throttle_ms cannot be negative")
        if self.queue_capacity <= 0:
            raise ValueError("queue_capacity must be greater than zero")
        if self.heartbeat_interval_seconds <= 0:
            raise ValueError("heartbeat_interval_seconds must be greater than zero")


@dataclass(frozen=True, slots=True)
class _QueuedEvent:
    sequence: int
    event: str
    frame: bytes
    terminal: bool


@dataclass(frozen=True, slots=True)
class _PendingEvent:
    payload: GenerationEventPayload


class GenerationSseSession:
    """One request-scoped, thread-safe generation event stream."""

    def __init__(
        self,
        *,
        job_id: str,
        loop: asyncio.AbstractEventLoop,
        settings: GenerationStreamSettings = GenerationStreamSettings(),
    ) -> None:
        self.job_id = job_id
        self._loop = loop
        self._settings = settings
        self._queue: deque[_QueuedEvent] = deque()
        self._queue_ready = asyncio.Event()
        self._pending: dict[str, _PendingEvent] = {}
        self._last_sent_at: dict[str, float] = {}
        self._flush_handles: dict[str, asyncio.TimerHandle] = {}
        self._sequence = 0
        self._terminal_queued = False
        self._delivery_open = True
        self._producer_task: asyncio.Task[None] | None = None

    def retain_producer(self, task: asyncio.Task[None]) -> None:
        self._producer_task = task
        task.add_done_callback(self._release_producer)

    def status(self, status: GenerationStatus) -> int | None:
        return self._submit(StatusPayload(status=status))

    def candidate_trial(
        self,
        *,
        trial_number: int,
        trial_limit: int,
        candidate_hints: tuple[CandidatePoint, ...],
    ) -> int | None:
        return self._submit(
            CandidateTrialPayload(
                trial_number=trial_number,
                trial_limit=trial_limit,
                candidate_hints=candidate_hints,
            )
        )

    def progress(
        self,
        *,
        stage: str,
        trial_number: int,
        trial_limit: int,
        elapsed_ms: int,
        timeout_ms: int,
    ) -> int | None:
        return self._submit(
            ProgressPayload(
                stage=stage,
                trial_number=trial_number,
                trial_limit=trial_limit,
                elapsed_ms=elapsed_ms,
                timeout_ms=timeout_ms,
            )
        )

    def floor_plan(
        self,
        *,
        classification: FloorPlanClassification,
        trial_number: int | None,
        candidate_id: int,
        solver_run_id: int,
        score: float,
        passed_critical: bool,
        floor_plan: FloorPlan,
    ) -> int | None:
        return self._submit(
            FloorPlanPayload(
                classification=classification,
                trial_number=trial_number,
                candidate_id=candidate_id,
                solver_run_id=solver_run_id,
                score=score,
                passed_critical=passed_critical,
                floor_plan=floor_plan,
            )
        )

    def completed(
        self,
        *,
        outcome: CompletionOutcome,
        final_floor_plan_sequence: int | None,
        elapsed_ms: int,
    ) -> int | None:
        return self._submit(
            CompletedPayload(
                outcome=outcome,
                final_floor_plan_sequence=final_floor_plan_sequence,
                elapsed_ms=elapsed_ms,
            )
        )

    def error(
        self,
        *,
        stage: str,
        code: str,
        message: str,
        recoverable: bool = False,
    ) -> int | None:
        return self._submit(
            ErrorPayload(
                stage=stage,
                code=code,
                message=message,
                recoverable=recoverable,
            )
        )

    async def iter_sse(self, request: Request) -> AsyncIterator[bytes]:
        try:
            while self._delivery_open:
                while self._queue:
                    queued = self._queue.popleft()
                    yield queued.frame
                    if queued.terminal:
                        self._detach_delivery()
                        return

                self._queue_ready.clear()
                if self._queue:
                    self._queue_ready.set()
                    continue

                try:
                    await asyncio.wait_for(
                        self._queue_ready.wait(),
                        timeout=self._settings.heartbeat_interval_seconds,
                    )
                except TimeoutError:
                    if await request.is_disconnected():
                        self._detach_delivery()
                        return
                    yield b": keep-alive\n\n"
        finally:
            self._detach_delivery()

    def _submit(self, payload: GenerationEventPayload) -> int | None:
        if not self._delivery_open or self._terminal_queued:
            return None

        result: Future[int | None] = Future()
        try:
            self._loop.call_soon_threadsafe(self._accept, payload, result)
        except RuntimeError:
            return None
        return result.result()

    def _accept(
        self,
        payload: GenerationEventPayload,
        result: Future[int | None],
    ) -> None:
        try:
            self._accept_event(payload, result)
        except Exception as exc:
            result.set_exception(exc)

    def _accept_event(
        self,
        payload: GenerationEventPayload,
        result: Future[int | None],
    ) -> None:
        if not self._delivery_open or self._terminal_queued:
            result.set_result(None)
            return

        name = event_name(payload)
        if name in {"completed", "error"}:
            self._flush_pending()
            self._terminal_queued = True
            result.set_result(self._enqueue(payload, terminal=True))
            return

        throttle_seconds = self._throttle_seconds(name)
        now = self._loop.time()
        last_sent = self._last_sent_at.get(name)
        if (
            throttle_seconds > 0
            and last_sent is not None
            and now - last_sent < throttle_seconds
        ):
            self._pending[name] = _PendingEvent(payload=payload)
            self._schedule_flush(name, last_sent + throttle_seconds)
            result.set_result(None)
            return

        sequence = self._enqueue(payload)
        if sequence is not None:
            self._last_sent_at[name] = now
        result.set_result(sequence)

    def _schedule_flush(self, name: str, flush_at: float) -> None:
        if name in self._flush_handles:
            return
        delay = max(0.0, flush_at - self._loop.time())
        self._flush_handles[name] = self._loop.call_later(
            delay,
            self._flush_group,
            name,
        )

    def _flush_group(self, name: str) -> None:
        self._flush_handles.pop(name, None)
        pending = self._pending.pop(name, None)
        if pending is None or not self._delivery_open or self._terminal_queued:
            return
        if self._enqueue(pending.payload) is not None:
            self._last_sent_at[name] = self._loop.time()

    def _flush_pending(self) -> None:
        for handle in self._flush_handles.values():
            handle.cancel()
        self._flush_handles.clear()
        pending = tuple(self._pending.values())
        self._pending.clear()
        for item in pending:
            name = event_name(item.payload)
            if self._enqueue(item.payload) is not None:
                self._last_sent_at[name] = self._loop.time()

    def _enqueue(
        self,
        payload: GenerationEventPayload,
        *,
        terminal: bool = False,
    ) -> int | None:
        name = event_name(payload)
        capacity_limit = (
            self._settings.queue_capacity
            if terminal
            else max(1, self._settings.queue_capacity - 1)
        )
        if len(self._queue) >= capacity_limit:
            if not self._make_room(name, terminal=terminal):
                return None

        self._sequence += 1
        sequence = self._sequence
        self._queue.append(
            _QueuedEvent(
                sequence=sequence,
                event=name,
                frame=self._format_frame(sequence, name, payload),
                terminal=terminal,
            )
        )
        self._queue_ready.set()
        return sequence

    def _make_room(self, name: str, *, terminal: bool) -> bool:
        for replaceable in ("candidate_trial", "progress", "status"):
            for index, queued in enumerate(self._queue):
                if queued.event == replaceable:
                    del self._queue[index]
                    return True

        if terminal and self._queue:
            self._queue.popleft()
            return True

        if name == "floor_plan":
            for index, queued in enumerate(self._queue):
                if queued.event == "floor_plan":
                    del self._queue[index]
                    return True
        return False

    def _format_frame(
        self,
        sequence: int,
        name: str,
        payload: GenerationEventPayload,
    ) -> bytes:
        timestamp = datetime.now(UTC).isoformat(timespec="milliseconds").replace(
            "+00:00",
            "Z",
        )
        envelope = {
            "schema_version": 1,
            "sequence": sequence,
            "timestamp": timestamp,
            "job_id": self.job_id,
            "event": name,
            "payload": payload,
        }
        data = json.dumps(
            to_json_value(envelope),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return f"id: {sequence}\nevent: {name}\ndata: {data}\n\n".encode()

    def _throttle_seconds(self, name: str) -> float:
        if name == "candidate_trial":
            return self._settings.candidate_trial_throttle_ms / 1000
        if name == "progress":
            return self._settings.progress_throttle_ms / 1000
        return 0.0

    def _detach_delivery(self) -> None:
        if not self._delivery_open:
            return
        self._delivery_open = False
        for handle in self._flush_handles.values():
            handle.cancel()
        self._flush_handles.clear()
        self._pending.clear()
        self._queue.clear()
        self._queue_ready.set()

    def _release_producer(self, task: asyncio.Task[None]) -> None:
        try:
            task.exception()
        except (asyncio.CancelledError, Exception):
            pass
        self._producer_task = None

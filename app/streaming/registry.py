from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from threading import Lock
from typing import Any

from .cancellation import GenerationCancellationToken


class CancellationRequestStatus(str, Enum):
    REQUESTED = "cancellation_requested"
    ALREADY_REQUESTED = "already_requested"
    NOT_FOUND = "not_found"


@dataclass(frozen=True, slots=True)
class CancellationRequestResult:
    job_id: str
    status: CancellationRequestStatus


@dataclass(frozen=True, slots=True)
class _ActiveGenerationJob:
    cancellation: GenerationCancellationToken
    close_stream: Callable[[str], Any] | None


class GenerationStreamRegistry:
    """Process-local registry of actively running streamed generation jobs."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._jobs: dict[str, _ActiveGenerationJob] = {}

    def register(
        self,
        job_id: str,
        *,
        close_stream: Callable[[str], Any] | None = None,
    ) -> GenerationCancellationToken:
        normalized_job_id = job_id.strip()
        if not normalized_job_id:
            raise ValueError("job_id cannot be empty")

        token = GenerationCancellationToken()
        active_job = _ActiveGenerationJob(
            cancellation=token,
            close_stream=close_stream,
        )
        with self._lock:
            if normalized_job_id in self._jobs:
                raise ValueError(
                    f"A streamed generation job with id '{normalized_job_id}' "
                    "is already registered"
                )
            self._jobs[normalized_job_id] = active_job
        return token

    def unregister(
        self,
        job_id: str,
        *,
        token: GenerationCancellationToken | None = None,
    ) -> None:
        with self._lock:
            active_job = self._jobs.get(job_id)
            if active_job is None:
                return
            if token is not None and active_job.cancellation is not token:
                return
            del self._jobs[job_id]

    def request_cancellation(
        self,
        job_id: str,
        *,
        reason: str = "client_request",
    ) -> CancellationRequestResult:
        with self._lock:
            active_job = self._jobs.get(job_id)

        if active_job is None:
            return CancellationRequestResult(
                job_id=job_id,
                status=CancellationRequestStatus.NOT_FOUND,
            )

        requested = active_job.cancellation.request_cancellation(reason=reason)
        if requested and active_job.close_stream is not None:
            try:
                active_job.close_stream(reason)
            except Exception:
                # The cancellation token is authoritative. Failure to enqueue
                # the terminal SSE frame must not undo the cancellation request.
                pass

        return CancellationRequestResult(
            job_id=job_id,
            status=(
                CancellationRequestStatus.REQUESTED
                if requested
                else CancellationRequestStatus.ALREADY_REQUESTED
            ),
        )

    def is_active(self, job_id: str) -> bool:
        with self._lock:
            return job_id in self._jobs


# The current streamed-generation implementation is process-local, so the
# active-job registry follows that same lifecycle.
generation_stream_registry = GenerationStreamRegistry()

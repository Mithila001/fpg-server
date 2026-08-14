from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol


class JobState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    CANCELLATION_REQUESTED = "cancellation_requested"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"

    @property
    def terminal(self) -> bool:
        return self in {
            JobState.COMPLETED,
            JobState.FAILED,
            JobState.CANCELLED,
            JobState.TIMED_OUT,
        }


class EventType(StrEnum):
    JOB = "job"
    STAGE = "stage"
    CANDIDATE = "candidate"
    FLOOR_PLAN = "floor_plan"
    ATTEMPT_ERROR = "attempt_error"
    TERMINAL = "terminal"


@dataclass(frozen=True, slots=True)
class EventError:
    code: str
    message: str
    recoverable: bool
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GenerationEvent:
    job_id: str
    sequence: int
    event_type: EventType
    stage: str
    state: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    error: EventError | None = None
    trial_number: int | None = None
    candidate_id: int | None = None
    timestamp_utc: datetime = field(default_factory=lambda: datetime.now(UTC))
    schema_version: str = "1.0"


@dataclass(frozen=True, slots=True)
class WorkerEvent:
    event_type: EventType
    stage: str
    state: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    error: EventError | None = None
    trial_number: int | None = None
    candidate_id: int | None = None


class GenerationEventPublisher(Protocol):
    def publish(self, event: WorkerEvent) -> None: ...


class NullGenerationEventPublisher:
    def publish(self, event: WorkerEvent) -> None:
        del event


__all__ = [
    "EventError",
    "EventType",
    "GenerationEvent",
    "GenerationEventPublisher",
    "JobState",
    "NullGenerationEventPublisher",
    "WorkerEvent",
]

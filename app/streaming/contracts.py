from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from app.algorithms.candidate_search import CandidatePoint
from app.algorithms.types_new import FloorPlan


class GenerationStatus(str, Enum):
    JOB_STARTED = "job_started"
    CANDIDATE_SEARCH_STARTED = "candidate_search_started"
    FLOOR_PLAN_GENERATION_STARTED = "floor_plan_generation_started"
    USABLE_FLOOR_PLAN_FOUND = "usable_floor_plan_found"
    PRESENTABLE_FLOOR_PLAN_FOUND = "presentable_floor_plan_found"
    TIMEOUT_REACHED = "timeout_reached"


class FloorPlanClassification(str, Enum):
    USABLE = "usable"
    PRESENTABLE = "presentable"


class CompletionOutcome(str, Enum):
    PRESENTABLE_PLAN_FOUND = "presentable_plan_found"
    BEST_USABLE_PLAN_RETURNED = "best_usable_plan_returned"


@dataclass(frozen=True, slots=True)
class StatusPayload:
    status: GenerationStatus


@dataclass(frozen=True, slots=True)
class CandidateTrialPayload:
    trial_number: int
    trial_limit: int
    candidate_hints: tuple[CandidatePoint, ...]


@dataclass(frozen=True, slots=True)
class ProgressPayload:
    stage: str
    trial_number: int
    trial_limit: int
    elapsed_ms: int
    timeout_ms: int


@dataclass(frozen=True, slots=True)
class FloorPlanPayload:
    classification: FloorPlanClassification
    trial_number: int | None
    candidate_id: int
    solver_run_id: int
    score: float
    passed_critical: bool
    floor_plan: FloorPlan


@dataclass(frozen=True, slots=True)
class CompletedPayload:
    outcome: CompletionOutcome
    final_floor_plan_sequence: int | None
    elapsed_ms: int


@dataclass(frozen=True, slots=True)
class ErrorPayload:
    stage: str
    code: str
    message: str
    recoverable: bool


GenerationEventPayload = (
    StatusPayload
    | CandidateTrialPayload
    | ProgressPayload
    | FloorPlanPayload
    | CompletedPayload
    | ErrorPayload
)


class GenerationEventPublisher(Protocol):
    def status(self, status: GenerationStatus) -> int | None: ...

    def candidate_trial(
        self,
        *,
        trial_number: int,
        trial_limit: int,
        candidate_hints: tuple[CandidatePoint, ...],
    ) -> int | None: ...

    def progress(
        self,
        *,
        stage: str,
        trial_number: int,
        trial_limit: int,
        elapsed_ms: int,
        timeout_ms: int,
    ) -> int | None: ...

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
    ) -> int | None: ...

    def completed(
        self,
        *,
        outcome: CompletionOutcome,
        final_floor_plan_sequence: int | None,
        elapsed_ms: int,
    ) -> int | None: ...

    def error(
        self,
        *,
        stage: str,
        code: str,
        message: str,
        recoverable: bool = False,
    ) -> int | None: ...


class NullGenerationEventPublisher:
    def status(self, status: GenerationStatus) -> int | None:
        return None

    def candidate_trial(
        self,
        *,
        trial_number: int,
        trial_limit: int,
        candidate_hints: tuple[CandidatePoint, ...],
    ) -> int | None:
        return None

    def progress(
        self,
        *,
        stage: str,
        trial_number: int,
        trial_limit: int,
        elapsed_ms: int,
        timeout_ms: int,
    ) -> int | None:
        return None

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
        return None

    def completed(
        self,
        *,
        outcome: CompletionOutcome,
        final_floor_plan_sequence: int | None,
        elapsed_ms: int,
    ) -> int | None:
        return None

    def error(
        self,
        *,
        stage: str,
        code: str,
        message: str,
        recoverable: bool = False,
    ) -> int | None:
        return None


def event_name(payload: GenerationEventPayload) -> str:
    if isinstance(payload, StatusPayload):
        return "status"
    if isinstance(payload, CandidateTrialPayload):
        return "candidate_trial"
    if isinstance(payload, ProgressPayload):
        return "progress"
    if isinstance(payload, FloorPlanPayload):
        return "floor_plan"
    if isinstance(payload, CompletedPayload):
        return "completed"
    return "error"

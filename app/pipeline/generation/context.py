from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping, Protocol

from fpg_core.floor_plan_scoring import FloorPlanScoringResult
from fpg_core.domain import FloorPlan, RoomType


class GenerationStage(StrEnum):
    PREPROCESSING = "preprocessing"
    CANDIDATE_SEARCH = "candidate_search"
    CANDIDATE_CIRCULATION = "candidate_circulation"
    CANDIDATE_SCORING = "candidate_scoring"
    INITIAL_GENERATION = "initial_generation"
    REFINEMENT_A = "refinement_a"
    REFINEMENT_B = "refinement_b"
    POST_PROCESSING = "post_processing"
    OPENINGS = "openings"
    FINAL_SCORING = "final_scoring"
    GENERATION = "generation"


class CancellationSignal(Protocol):
    def is_set(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class RequestedGenerationRoom:
    room_type: RoomType
    id: str | None = None
    name: str | None = None
    requested_size: str | None = None


@dataclass(frozen=True, slots=True)
class GenerationPipelineRequest:
    job_id: str
    flow_directory: str
    max_width: int
    max_length: int
    aspect_ratio: float | str
    rooms: tuple[RequestedGenerationRoom, ...]


@dataclass(frozen=True, slots=True)
class GenerationPipelineResult:
    floor_plan: FloorPlan
    scoring: FloorPlanScoringResult
    classification: str
    outcome: str


class GenerationPipelineError(Exception):
    def __init__(
        self,
        stage: GenerationStage,
        code: str,
        message: str,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.stage = stage
        self.code = code
        self.message = message
        self.details = MappingProxyType(dict(details or {}))


__all__ = [
    "CancellationSignal",
    "GenerationPipelineError",
    "GenerationPipelineRequest",
    "GenerationPipelineResult",
    "GenerationStage",
    "RequestedGenerationRoom",
]

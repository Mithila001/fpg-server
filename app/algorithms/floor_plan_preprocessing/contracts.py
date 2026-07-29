from __future__ import annotations

from dataclasses import dataclass

from app.algorithms.types_new import (
    ConstraintStrength,
    FloorPlanGenerationSpec,
    MatchPolicy,
    RoomType,
)
from app.core.execution import ExecutionContext

from .config import PreprocessingPolicy


@dataclass(frozen=True, slots=True)
class FloorLimits:
    max_width: float
    max_length: float


@dataclass(frozen=True, slots=True)
class RequestedRoom:
    room_type: RoomType
    id: str | None = None
    name: str | None = None
    requested_size: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.room_type, RoomType):
            raise TypeError("room_type must be a RoomType enum member")


@dataclass(frozen=True, slots=True)
class PreprocessingRequest:
    floor_limits: FloorLimits
    aspect_ratio: float | str
    rooms: tuple[RequestedRoom, ...]


@dataclass(frozen=True, slots=True)
class RoomSizeReference:
    room_type: RoomType
    size: str
    min_width: float
    max_width: float
    min_area: float
    max_area: float

    def __post_init__(self) -> None:
        if not isinstance(self.room_type, RoomType):
            raise TypeError("room_type must be a RoomType enum member")


@dataclass(frozen=True, slots=True)
class RoomRelationReference:
    source_room_type: RoomType
    target_room_types: tuple[RoomType, ...]
    match_policy: MatchPolicy | str
    strength: ConstraintStrength | str
    required: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.source_room_type, RoomType):
            raise TypeError("source_room_type must be a RoomType enum member")
        if any(not isinstance(value, RoomType) for value in self.target_room_types):
            raise TypeError("target_room_types must contain only RoomType enum members")


@dataclass(frozen=True, slots=True)
class PreprocessingReferenceData:
    room_sizes: tuple[RoomSizeReference, ...]
    room_relations: tuple[RoomRelationReference, ...] = ()


@dataclass(frozen=True, slots=True)
class PreprocessingInput:
    request: PreprocessingRequest
    reference_data: PreprocessingReferenceData
    policy: PreprocessingPolicy = PreprocessingPolicy()
    execution_context: ExecutionContext | None = None


@dataclass(frozen=True, slots=True)
class NormalizationRecord:
    field: str
    original: str
    normalized: str


@dataclass(frozen=True, slots=True)
class RoomDecision:
    room_id: str
    room_type: RoomType
    action: str
    reason: str


@dataclass(frozen=True, slots=True)
class RelationDecision:
    source_room_type: RoomType
    action: str
    detail: str


@dataclass(frozen=True, slots=True)
class FloorSelection:
    requested_width: float
    requested_length: float
    selected_width: float
    selected_length: float
    aspect_ratio: float
    minimum_required_area: float
    maximum_target_area: float


@dataclass(frozen=True, slots=True)
class PreprocessingReport:
    normalizations: tuple[NormalizationRecord, ...]
    room_decisions: tuple[RoomDecision, ...]
    relation_decisions: tuple[RelationDecision, ...]
    selected_room_size: str
    floor_selection: FloorSelection
    applied_defaults: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PreparedGenerationInput:
    generation_spec: FloorPlanGenerationSpec
    report: PreprocessingReport

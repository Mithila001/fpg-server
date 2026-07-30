from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from fpg_core import FpgCoreConfig
from fpg_core.types_new import RoomType

from app.artifacts import ArtifactStorage
from app.pipeline.generation import (
    GenerationPipelineRequest,
    GenerationPipelineResult,
    RequestedGenerationRoom,
    run_generation_pipeline,
)
from app.streaming.cancellation import GenerationCancellationSignal
from app.streaming.contracts import (
    GenerationEventPublisher,
    NullGenerationEventPublisher,
)


@dataclass(frozen=True, slots=True)
class GenerationServiceRoom:
    room_type: RoomType
    id: str | None = None
    name: str | None = None
    requested_size: str | None = "regular"

    def __post_init__(self) -> None:
        if not isinstance(self.room_type, RoomType):
            raise TypeError("room_type must be a RoomType enum member")


@dataclass(frozen=True, slots=True)
class GenerationServiceRequest:
    max_width: float
    max_length: float
    aspect_ratio: float | str
    rooms: tuple[GenerationServiceRoom, ...]


@dataclass(frozen=True, slots=True)
class GenerationRoomSizeConstraint:
    room_type: RoomType
    size: str
    min_width: float
    max_width: float
    min_area: float
    max_area: float


class GenerationReferenceDataUnavailableError(RuntimeError):
    pass


def get_generation_room_size_constraints(
    core_config: FpgCoreConfig,
) -> tuple[GenerationRoomSizeConstraint, ...]:
    """Return the validated room-size constraints used by preprocessing."""

    return tuple(
        GenerationRoomSizeConstraint(
            room_type=reference.room_type,
            size=reference.size,
            min_width=float(reference.min_width),
            max_width=float(reference.max_width),
            min_area=float(reference.min_area),
            max_area=float(reference.max_area),
        )
        for reference in core_config.preprocessing.room_sizes
    )


def execute_generation(
    request: GenerationServiceRequest,
    *,
    core_config: FpgCoreConfig,
    job_id: str | None = None,
    events: GenerationEventPublisher | None = None,
    cancellation: GenerationCancellationSignal | None = None,
) -> GenerationPipelineResult:
    resolved_job_id = job_id or str(uuid4())
    execution_context = ArtifactStorage().create_execution_context(
        job_id=resolved_job_id
    )
    pipeline_request = GenerationPipelineRequest(
        request_id=resolved_job_id,
        max_width=request.max_width,
        max_length=request.max_length,
        aspect_ratio=request.aspect_ratio,
        rooms=tuple(
            RequestedGenerationRoom(
                room_type=room.room_type,
                id=room.id,
                name=room.name,
                requested_size=room.requested_size,
            )
            for room in request.rooms
        ),
        execution_context=execution_context,
    )
    return run_generation_pipeline(
        pipeline_request,
        core_config=core_config,
        events=events or NullGenerationEventPublisher(),
        cancellation=cancellation,
    )

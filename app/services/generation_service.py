from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.algorithms.types_new import RoomType
from app.artifacts import ArtifactStorage
from app.pipeline.generation import (
    GenerationPipelineRequest,
    GenerationPipelineResult,
    RequestedGenerationRoom,
    run_generation_pipeline,
)
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
    required: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.room_type, RoomType):
            raise TypeError("room_type must be a RoomType enum member")


@dataclass(frozen=True, slots=True)
class GenerationServiceRequest:
    max_width: float
    max_length: float
    aspect_ratio: float | str
    rooms: tuple[GenerationServiceRoom, ...]


def execute_generation(
    request: GenerationServiceRequest,
    *,
    job_id: str | None = None,
    events: GenerationEventPublisher | None = None,
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
                required=room.required,
            )
            for room in request.rooms
        ),
        execution_context=execution_context,
    )
    return run_generation_pipeline(
        pipeline_request,
        events=events or NullGenerationEventPublisher(),
    )

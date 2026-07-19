from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.algorithms.types_new import RoomType
from app.pipeline.generation import (
    GenerationPipelineRequest,
    GenerationPipelineResult,
    RequestedGenerationRoom,
    run_generation_pipeline,
)


@dataclass(frozen=True, slots=True)
class GenerationServiceRoom:
    room_type: RoomType
    id: str | None = None
    name: str | None = None
    requested_size: str | None = "regular"
    required: bool = True


@dataclass(frozen=True, slots=True)
class GenerationServiceRequest:
    max_width: float
    max_height: float
    aspect_ratio: float | str
    rooms: tuple[GenerationServiceRoom, ...]


def execute_generation(
    request: GenerationServiceRequest,
) -> GenerationPipelineResult:
    pipeline_request = GenerationPipelineRequest(
        request_id=str(uuid4()),
        max_width=request.max_width,
        max_height=request.max_height,
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
    )
    return run_generation_pipeline(pipeline_request)

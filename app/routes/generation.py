from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.algorithms.types_new import RoomType
from app.pipeline.generation import GenerationPipelineError
from app.services.generation_service import (
    GenerationServiceRequest,
    GenerationServiceRoom,
    execute_generation,
)
from app.streaming import GenerationStatus
from app.streaming.session import GenerationSseSession

router = APIRouter(tags=["generation"])


class FloorLimitsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_width: float = Field(gt=0)
    max_length: float = Field(gt=0)


class GenerationRoomRequest(BaseModel):
    room_type: RoomType
    id: str | None = None
    name: str | None = None
    requested_size: str | None = Field(default="regular", min_length=1)
    required: bool = True


class GenerationRequest(BaseModel):
    floor_limits: FloorLimitsRequest
    aspect_ratio: float | str
    rooms: list[GenerationRoomRequest] = Field(min_length=1)


class GenerationResponse(BaseModel):
    floor_plan: dict[str, Any]
    scoring: dict[str, Any]


class GenerationErrorResponse(BaseModel):
    stage: str
    code: str
    message: str
    details: dict[str, Any] | None = None


def _to_service_request(body: GenerationRequest) -> GenerationServiceRequest:
    return GenerationServiceRequest(
        max_width=body.floor_limits.max_width,
        max_length=body.floor_limits.max_length,
        aspect_ratio=body.aspect_ratio,
        rooms=tuple(
            GenerationServiceRoom(
                room_type=room.room_type,
                id=room.id,
                name=room.name,
                requested_size=room.requested_size,
                required=room.required,
            )
            for room in body.rooms
        ),
    )


@router.post(
    "/generation",
    response_model=GenerationResponse,
    responses={422: {"model": GenerationErrorResponse}},
)
def generate(body: GenerationRequest) -> GenerationResponse | JSONResponse:
    try:
        result = execute_generation(_to_service_request(body))
    except GenerationPipelineError as exc:
        return JSONResponse(
            status_code=422,
            content=jsonable_encoder(
                GenerationErrorResponse(
                    stage=exc.stage.value,
                    code=exc.code,
                    message=exc.message,
                    details=dict(exc.details) or None,
                )
            ),
        )
    except Exception:
        return JSONResponse(
            status_code=500,
            content={"message": "Generation failed unexpectedly."},
        )

    return GenerationResponse(
        floor_plan=jsonable_encoder(result.floor_plan),
        scoring=jsonable_encoder(result.scoring),
    )


@router.post("/generation/stream", response_class=StreamingResponse)
async def stream_generation(
    body: GenerationRequest,
    request: Request,
) -> StreamingResponse:
    job_id = str(uuid4())
    session = GenerationSseSession(
        job_id=job_id,
        loop=asyncio.get_running_loop(),
    )
    producer = asyncio.create_task(
        asyncio.to_thread(
            _produce_stream,
            _to_service_request(body),
            job_id,
            session,
        )
    )
    session.retain_producer(producer)

    return StreamingResponse(
        session.iter_sse(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Generation-Job-ID": job_id,
        },
    )


def _produce_stream(
    service_request: GenerationServiceRequest,
    job_id: str,
    events: GenerationSseSession,
) -> None:
    try:
        execute_generation(
            service_request,
            job_id=job_id,
            events=events,
        )
    except GenerationPipelineError as exc:
        if exc.details.get("termination_reason") == "timeout":
            events.status(GenerationStatus.TIMEOUT_REACHED)
        events.error(
            stage=exc.stage.value,
            code=exc.code,
            message=exc.message,
        )
    except Exception:
        events.error(
            stage="generation",
            code="unexpected_generation_error",
            message="Generation failed unexpectedly.",
        )

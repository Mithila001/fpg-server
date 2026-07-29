from __future__ import annotations

import asyncio
from enum import Enum
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.algorithms.types_new import RoomType
from app.pipeline.generation import GenerationPipelineError
from app.services.generation_service import (
    GenerationReferenceDataUnavailableError,
    GenerationServiceRequest,
    GenerationServiceRoom,
    execute_generation,
    get_generation_room_size_constraints,
)
from app.streaming import (
    CancellationRequestStatus,
    GenerationCancellationToken,
    GenerationStatus,
    generation_stream_registry,
)
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


class MessageResponse(BaseModel):
    message: str


class GenerationRoomSizeConstraintResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room_type: RoomType
    size: str
    min_width: float
    max_width: float
    min_area: float
    max_area: float


class GenerationRoomSizeConstraintsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room_size_constraints: list[GenerationRoomSizeConstraintResponse]


class GenerationCancellationStatus(str, Enum):
    CANCELLATION_REQUESTED = "cancellation_requested"
    ALREADY_REQUESTED = "already_requested"


class GenerationCancellationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    status: GenerationCancellationStatus


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


@router.get(
    "/generation/room-size-constraints",
    response_model=GenerationRoomSizeConstraintsResponse,
    responses={500: {"model": MessageResponse}},
)
def get_room_size_constraints(
) -> GenerationRoomSizeConstraintsResponse | JSONResponse:
    try:
        constraints = get_generation_room_size_constraints()
    except GenerationReferenceDataUnavailableError:
        return JSONResponse(
            status_code=500,
            content={
                "message": (
                    "Generation room-size constraints are currently unavailable."
                )
            },
        )

    return GenerationRoomSizeConstraintsResponse(
        room_size_constraints=[
            GenerationRoomSizeConstraintResponse(
                room_type=constraint.room_type,
                size=constraint.size,
                min_width=constraint.min_width,
                max_width=constraint.max_width,
                min_area=constraint.min_area,
                max_area=constraint.max_area,
            )
            for constraint in constraints
        ]
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
    cancellation = generation_stream_registry.register(
        job_id,
        close_stream=lambda reason: session.cancelled(reason=reason),
    )

    try:
        producer = asyncio.create_task(
            asyncio.to_thread(
                _produce_stream,
                _to_service_request(body),
                job_id,
                session,
                cancellation,
            )
        )
    except Exception:
        generation_stream_registry.unregister(job_id, token=cancellation)
        raise

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


@router.delete(
    "/generation/stream/{job_id}",
    response_model=GenerationCancellationResponse,
    responses={
        202: {"model": GenerationCancellationResponse},
        404: {"model": MessageResponse},
    },
)
def cancel_stream_generation(
    job_id: str,
) -> GenerationCancellationResponse | JSONResponse:
    result = generation_stream_registry.request_cancellation(
        job_id,
        reason="client_request",
    )

    if result.status is CancellationRequestStatus.NOT_FOUND:
        return JSONResponse(
            status_code=404,
            content={
                "message": "No active streamed generation job was found.",
            },
        )

    response_status = (
        GenerationCancellationStatus.CANCELLATION_REQUESTED
        if result.status is CancellationRequestStatus.REQUESTED
        else GenerationCancellationStatus.ALREADY_REQUESTED
    )
    response = GenerationCancellationResponse(
        job_id=result.job_id,
        status=response_status,
    )

    if result.status is CancellationRequestStatus.REQUESTED:
        return JSONResponse(
            status_code=202,
            content=jsonable_encoder(response),
        )
    return response


def _produce_stream(
    service_request: GenerationServiceRequest,
    job_id: str,
    events: GenerationSseSession,
    cancellation: GenerationCancellationToken,
) -> None:
    try:
        execute_generation(
            service_request,
            job_id=job_id,
            events=events,
            cancellation=cancellation,
        )
    except GenerationPipelineError as exc:
        termination_reason = exc.details.get("termination_reason")
        if termination_reason == "cancelled":
            events.cancelled(
                reason=str(exc.details.get("reason") or "client_request")
            )
            return
        if termination_reason == "timeout":
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
    finally:
        generation_stream_registry.unregister(job_id, token=cancellation)

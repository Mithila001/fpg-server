from __future__ import annotations

import asyncio
from enum import Enum
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse
from fpg_core import FpgCoreConfig
from fpg_core.types_new import RoadType, RoomType
from pydantic import BaseModel, ConfigDict, Field

from app.core_config import CoreConfigLoadError, get_fpg_core_config
from app.pipeline.generation import GenerationPipelineError
from app.routes.errors import (
    ApiErrorCode,
    ApiErrorResponse,
    api_error_response,
)
from app.services.generation_service import (
    GenerationServiceRequest,
    GenerationServiceRoom,
    execute_generation,
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
    model_config = ConfigDict(extra="forbid")

    room_type: RoomType
    id: str | None = None
    name: str | None = None
    requested_size: str | None = Field(default="regular", min_length=1)


class GenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    floor_limits: FloorLimitsRequest
    aspect_ratio: float | str
    rooms: list[GenerationRoomRequest] = Field(min_length=1)


class GenerationResponse(BaseModel):
    floor_plan: dict[str, Any]
    scoring: dict[str, Any]


class RoomSizeMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room_type: RoomType
    size: str
    min_width: float
    max_width: float
    min_area: float
    max_area: float


class RoomRelationMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_room_type: RoomType
    target_room_types: list[RoomType]
    match_policy: str
    strength: str
    required: bool


class GenerationReferenceMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room_sizes: list[RoomSizeMetadata]
    room_relations: list[RoomRelationMetadata]


class RoadTypeMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: RoadType
    name: str
    display_name: str


class RoomRequirementMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room_type: RoomType
    name: str
    min_count: int
    max_count: int
    client_selectable: bool


class AspectRatioMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    value: float


class BufferMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hallway_area: float
    floor_area: float
    unit: str


class MetadataResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int
    generation_reference_data: GenerationReferenceMetadata
    road_types: list[RoadTypeMetadata]
    room_requirements: list[RoomRequirementMetadata]
    compatible_aspect_ratios: list[AspectRatioMetadata]
    buffers: BufferMetadata


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
            )
            for room in body.rooms
        ),
    )


@router.get(
    "/metadata",
    response_model=MetadataResponse,
    responses={500: {"model": ApiErrorResponse}},
)
def get_metadata(request: Request) -> MetadataResponse | JSONResponse:
    try:
        core_config = get_fpg_core_config(request.app)
    except CoreConfigLoadError:
        return api_error_response(
            status_code=500,
            code=ApiErrorCode.REFERENCE_DATA_UNAVAILABLE.value,
            message="Server metadata is currently unavailable.",
            stage="metadata",
        )
    generation = core_config.preprocessing
    buildable = core_config.buildable_space

    return MetadataResponse(
        schema_version=core_config.schema_version,
        generation_reference_data=GenerationReferenceMetadata(
            room_sizes=[
                RoomSizeMetadata(
                    room_type=item.room_type,
                    size=item.size,
                    min_width=float(item.min_width),
                    max_width=float(item.max_width),
                    min_area=float(item.min_area),
                    max_area=float(item.max_area),
                )
                for item in generation.room_sizes
            ],
            room_relations=[
                RoomRelationMetadata(
                    source_room_type=item.source_room_type,
                    target_room_types=list(item.target_room_types),
                    match_policy=str(
                        getattr(item.match_policy, "value", item.match_policy)
                    ),
                    strength=str(getattr(item.strength, "value", item.strength)),
                    required=item.required,
                )
                for item in generation.room_relations
            ],
        ),
        road_types=[
            RoadTypeMetadata(
                value=road_type,
                name=road_type.name,
                display_name=road_type.value.replace("_", " ").title(),
            )
            for road_type in buildable.active_profile.road_adjustments
        ],
        room_requirements=[
            RoomRequirementMetadata(
                room_type=item.room_type,
                name=item.room_type.name,
                min_count=item.minimum,
                max_count=item.maximum,
                client_selectable=item.client_selectable,
            )
            for item in generation.room_count_rules
        ],
        compatible_aspect_ratios=[
            AspectRatioMetadata(label=item.label, value=item.canonical_value)
            for item in generation.supported_aspect_ratios
        ],
        buffers=BufferMetadata(
            hallway_area=generation.hallway_area_buffer,
            floor_area=generation.floor_area_buffer,
            unit="square_project_units",
        ),
    )


@router.post(
    "/generation",
    response_model=GenerationResponse,
    responses={
        422: {"model": ApiErrorResponse},
        500: {"model": ApiErrorResponse},
    },
)
def generate(
    body: GenerationRequest, request: Request
) -> GenerationResponse | JSONResponse:
    try:
        result = execute_generation(
            _to_service_request(body),
            core_config=get_fpg_core_config(request.app),
        )
    except GenerationPipelineError as exc:
        status_code = 500 if exc.code == "invalid_reference_data" else 422
        return api_error_response(
            status_code=status_code,
            stage=exc.stage.value,
            code=exc.code,
            message=exc.message,
            details=dict(exc.details),
        )
    except Exception:
        return api_error_response(
            status_code=500,
            code=ApiErrorCode.UNEXPECTED_ERROR.value,
            message="Generation failed unexpectedly.",
            stage="generation",
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
                get_fpg_core_config(request.app),
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
        404: {"model": ApiErrorResponse},
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
        return api_error_response(
            status_code=404,
            code=ApiErrorCode.NOT_FOUND.value,
            message="No active streamed generation job was found.",
            stage="cancellation",
            details={"job_id": job_id},
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
    core_config: FpgCoreConfig,
) -> None:
    try:
        execute_generation(
            service_request,
            core_config=core_config,
            job_id=job_id,
            events=events,
            cancellation=cancellation,
        )
    except GenerationPipelineError as exc:
        termination_reason = exc.details.get("termination_reason")
        if termination_reason == "cancelled":
            events.cancelled(reason=str(exc.details.get("reason") or "client_request"))
            return
        if termination_reason == "timeout":
            events.status(GenerationStatus.TIMEOUT_REACHED)
        events.error(
            stage=exc.stage.value,
            code=exc.code,
            message=exc.message,
            details=dict(exc.details),
        )
    except Exception:
        events.error(
            stage="generation",
            code="unexpected_generation_error",
            message="Generation failed unexpectedly.",
            details={},
        )
    finally:
        generation_stream_registry.unregister(job_id, token=cancellation)

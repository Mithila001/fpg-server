from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fpg_core.domain import RoadType, RoomType
from pydantic import BaseModel, ConfigDict, Field, StrictInt

from app.core_config import CoreConfigLoadError, get_server_config
from app.jobs import (
    CancellationOutcome,
    GenerationJobManager,
    JobNotCancellableError,
    JobNotFoundError,
    QueueFullError,
)
from app.pipeline.generation import (
    GenerationPipelineRequest,
    RequestedGenerationRoom,
)
from app.routes.errors import ApiErrorCode, ApiErrorResponse, api_error_response

router = APIRouter(prefix="/api/v1", tags=["floor-plan-generation"])


class _ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FloorLimitsRequest(_ContractModel):
    max_width: StrictInt = Field(gt=0)
    max_length: StrictInt = Field(gt=0)


class GenerationRoomRequest(_ContractModel):
    room_type: RoomType
    id: str | None = Field(default=None, min_length=1)
    name: str | None = Field(default=None, min_length=1)
    requested_size: str | None = Field(default=None, min_length=1)


class GenerationRequest(_ContractModel):
    floor_limits: FloorLimitsRequest
    aspect_ratio: float | str
    rooms: list[GenerationRoomRequest] = Field(min_length=1)


class JobCreatedResponse(_ContractModel):
    job_id: str
    state: str
    status_url: str
    events_url: str
    cancellation_url: str


class JobResponse(_ContractModel):
    job_id: str
    state: str
    created_at: str
    started_at: str | None
    completed_at: str | None
    result: dict[str, Any] | None
    error: dict[str, Any] | None


class CancellationResponse(_ContractModel):
    job_id: str
    status: str


class RoomSizeMetadata(_ContractModel):
    room_type: RoomType
    size: str
    min_width: float
    max_width: float
    min_area: float
    max_area: float


class RoomRequirementMetadata(_ContractModel):
    room_type: RoomType
    min_count: int
    max_count: int
    client_selectable: bool


class MetadataResponse(_ContractModel):
    schema_version: int
    project_units_per_meter: int
    front_axis: str
    road_types: list[dict[str, str]]
    room_requirements: list[RoomRequirementMetadata]
    room_sizes: list[RoomSizeMetadata]
    compatible_aspect_ratios: list[dict[str, float | str]]


def _manager(request: Request) -> GenerationJobManager:
    manager = getattr(request.app.state, "job_manager", None)
    if not isinstance(manager, GenerationJobManager):
        raise RuntimeError("Generation job manager is unavailable.")
    return manager


@router.get(
    "/metadata",
    response_model=MetadataResponse,
    responses={500: {"model": ApiErrorResponse}},
)
def get_metadata(request: Request) -> MetadataResponse | JSONResponse:
    try:
        config = get_server_config(request.app)
    except CoreConfigLoadError:
        return api_error_response(
            500,
            ApiErrorCode.REFERENCE_DATA_UNAVAILABLE.value,
            "Server metadata is unavailable.",
            "metadata",
        )
    preprocessing = config.core.preprocessing
    return MetadataResponse(
        schema_version=config.core.schema_version,
        project_units_per_meter=10,
        front_axis="-Y",
        road_types=[
            {
                "value": road.value,
                "name": road.name,
                "display_name": road.value.replace("_", " ").title(),
            }
            for road in config.core.buildable_space.active_profile.road_adjustments
            if isinstance(road, RoadType)
        ],
        room_requirements=[
            RoomRequirementMetadata(
                room_type=rule.room_type,
                min_count=rule.minimum,
                max_count=rule.maximum,
                client_selectable=rule.client_selectable,
            )
            for rule in preprocessing.room_count_rules
        ],
        room_sizes=[
            RoomSizeMetadata(
                room_type=item.room_type,
                size=item.size,
                min_width=item.min_width,
                max_width=item.max_width,
                min_area=item.min_area,
                max_area=item.max_area,
            )
            for item in preprocessing.room_sizes
        ],
        compatible_aspect_ratios=[
            {"label": ratio.label, "value": ratio.canonical_value}
            for ratio in preprocessing.supported_aspect_ratios
        ],
    )


@router.post(
    "/floor-plan-jobs",
    status_code=202,
    response_model=JobCreatedResponse,
    responses={429: {"model": ApiErrorResponse}},
)
async def create_floor_plan_job(
    body: GenerationRequest, request: Request
) -> JobCreatedResponse | JSONResponse:
    pipeline_request = GenerationPipelineRequest(
        job_id="pending",
        flow_directory="",
        max_width=body.floor_limits.max_width,
        max_length=body.floor_limits.max_length,
        aspect_ratio=body.aspect_ratio,
        rooms=tuple(
            RequestedGenerationRoom(
                room_type=room.room_type,
                id=room.id,
                name=room.name,
                requested_size=room.requested_size,
            )
            for room in body.rooms
        ),
    )
    try:
        record = await _manager(request).create(pipeline_request)
    except QueueFullError:
        return api_error_response(
            429,
            "queue_full",
            "The floor-plan generation queue is full.",
            "job_creation",
        )
    base = f"/api/v1/floor-plan-jobs/{record.job_id}"
    return JobCreatedResponse(
        job_id=record.job_id,
        state=record.state.value,
        status_url=base,
        events_url=f"{base}/events",
        cancellation_url=base,
    )


@router.get(
    "/floor-plan-jobs/{job_id}",
    response_model=JobResponse,
    responses={404: {"model": ApiErrorResponse}},
)
async def get_floor_plan_job(
    job_id: str, request: Request
) -> JobResponse | JSONResponse:
    try:
        record = await _manager(request).get(job_id)
    except JobNotFoundError:
        return api_error_response(
            404, "job_not_found", "No retained generation job was found.", "job"
        )
    return JobResponse.model_validate(_manager(request).public_snapshot(record))


@router.get(
    "/floor-plan-jobs/{job_id}/events",
    response_model=None,
    response_class=StreamingResponse,
    responses={404: {"model": ApiErrorResponse}},
)
async def stream_floor_plan_job(
    job_id: str,
    request: Request,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> StreamingResponse | JSONResponse:
    try:
        after = int(last_event_id) if last_event_id is not None else 0
        if after < 0:
            raise ValueError
    except ValueError:
        return api_error_response(
            422,
            ApiErrorCode.INVALID_REQUEST.value,
            "Last-Event-ID must be a non-negative integer.",
            "request_validation",
        )
    manager = _manager(request)
    try:
        await manager.get(job_id)
    except JobNotFoundError:
        return api_error_response(
            404, "job_not_found", "No retained generation job was found.", "job"
        )
    return StreamingResponse(
        manager.events(job_id, after),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "X-Generation-Job-ID": job_id,
        },
    )


@router.delete(
    "/floor-plan-jobs/{job_id}",
    response_model=CancellationResponse,
    responses={404: {"model": ApiErrorResponse}, 409: {"model": ApiErrorResponse}},
)
async def cancel_floor_plan_job(
    job_id: str, request: Request
) -> CancellationResponse | JSONResponse:
    try:
        outcome = await _manager(request).cancel(job_id)
    except JobNotFoundError:
        return api_error_response(
            404, "job_not_found", "No retained generation job was found.", "cancellation"
        )
    except JobNotCancellableError:
        return api_error_response(
            409,
            "job_not_cancellable",
            "The generation job is already terminal.",
            "cancellation",
            {"job_id": job_id},
        )
    response = CancellationResponse(job_id=job_id, status=outcome.value)
    if outcome is CancellationOutcome.REQUESTED:
        return JSONResponse(status_code=202, content=response.model_dump())
    return response

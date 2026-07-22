from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.algorithms.types_new import RoomType
from app.pipeline.generation import GenerationPipelineError
from app.services.generation_service import (
    GenerationServiceRequest,
    GenerationServiceRoom,
    execute_generation,
)

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


@router.post(
    "/generation",
    response_model=GenerationResponse,
    responses={422: {"model": GenerationErrorResponse}},
)
def generate(body: GenerationRequest):
    try:
        result = execute_generation(
            GenerationServiceRequest(
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
        )
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

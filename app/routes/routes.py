from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from time import time

from app.algorithms.fpg_rooms.fpg_optuna.exceptions import TrialTimeoutError
from app.services.algorithm_manager import run_layout_pipeline
from app.services.algorithm_manager_v2 import run_fpg_pipeline_api
from app.schemas.db.room_setup_template import RoomSetupTemplateBase
from app.util.tracking import use_tracking_context
from app.util.unit_converter import (
    converter_cm_to_unit,
    converter_unit_to_centimeters,
    converter_unit_to_meters,
)
from app.util.room_requirements import floor_values
# Plotting hook removed so api_result_plotter is isolated and unused by default
# from test.dev.plotter_loader import plot_floor_plan_payload
# from app.util.logger import SystemLogger

# In-memory per-client rate limit tracker (simple, single-process)
_last_format_request: dict[str, float] = {}
_last_format_v2_request: dict[str, float] = {}
_rate_limit_seconds = 2


class PointResponse(BaseModel):
    x: float
    y: float
class WallSegmentResponse(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class OpeningSegmentResponse(BaseModel):
    room_name: str
    room_type: str | None = None
    opening_type: str | None = None
    side: str | None = None
    x1: float | None = None
    y1: float | None = None
    x2: float | None = None
    y2: float | None = None
    connected_room_name: str | None = None
    connected_room_type: str | None = None


class CompactRoomResponse(BaseModel):
    room_name: str
    room_type: str
    walls: List[WallSegmentResponse]
    openings: List[OpeningSegmentResponse]


class VerandaMetadataResponse(BaseModel):
    room_name: str
    l_veranda_pillar: PointResponse
    r_veranda_pillar: PointResponse
    veranda_back_points: List[PointResponse]


class PostProcessMetadataResponse(BaseModel):
    veranda: VerandaMetadataResponse | None = None
    garage_shared_horizontal_overlap_segment: WallSegmentResponse | None = None
    hallway_living_shared_walls: List[WallSegmentResponse] = Field(default_factory=list)
    converted_hallway_living_openings: int = 0


class FormatterResponse(BaseModel):
    status: str
    message: str
    walls: List[WallSegmentResponse]
    compact_by_room: dict[str, CompactRoomResponse]
    metadata: PostProcessMetadataResponse | None = None


class FormatterV2ApiRequest(BaseModel):
    floor_width: float
    floor_height: float
    room_template: RoomSetupTemplateBase
    should_optuna_run: bool = False
    optuna_trial_count: int = 20


router = APIRouter(prefix="/algorithms", tags=["algorithms"])


@router.get("/format", response_model=FormatterResponse)
def get_formatted_layout(request: Request):
    """Run the DB-backed solver and return post-processed wall layout payload."""
    client_ip = request.client.host if request.client else "unknown"
    now = time()
    last_call = _last_format_request.get(client_ip, 0)
    elapsed = now - last_call
    if elapsed < _rate_limit_seconds:
        retry_after = _rate_limit_seconds - elapsed
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {retry_after:.1f} seconds.",
            headers={"Retry-After": str(int(retry_after) + 1)},
        )
    _last_format_request[client_ip] = now

    payload = run_layout_pipeline(use_optuna=True, verbose=False)
    payload = converter_unit_to_meters(payload)

    # Plotting is disabled in this branch to keep api_result_plotter isolated.
    return FormatterResponse(**payload)


@router.post("/format/v2", response_model=FormatterResponse)
def get_formatted_layout_v2(request: Request, body: FormatterV2ApiRequest):
    """Run v2 API pipeline from request payload with simple per-client rate limiting."""
    client_ip = request.client.host if request.client else "unknown"
    now = time()
    last_call = _last_format_v2_request.get(client_ip, 0)
    elapsed = now - last_call
    if elapsed < _rate_limit_seconds:
        retry_after = _rate_limit_seconds - elapsed
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {retry_after:.1f} seconds.",
            headers={"Retry-After": str(int(retry_after) + 1)},
        )
    _last_format_v2_request[client_ip] = now

    try:
        with use_tracking_context():
            # Floor dimensions are converted from cm to units, then floored to integers
            floored_width = floor_values(converter_cm_to_unit(body.floor_width))
            floored_height = floor_values(converter_cm_to_unit(body.floor_height))
            
            payload = run_fpg_pipeline_api(
                floor_width=floored_width,
                floor_height=floored_height,
                room_template=body.room_template,
                should_optuna_run=body.should_optuna_run,
                optuna_trial_count=body.optuna_trial_count,
            )
        payload = converter_unit_to_centimeters(payload)

        # Plotting is disabled in this branch to keep api_result_plotter isolated.
        return FormatterResponse(**payload)
    except TrialTimeoutError as e:
        raise HTTPException(
            status_code=408,
            detail={
                "error": "trial_timeout",
                "message": str(e),
                "elapsed_time": e.elapsed_time,
                "timeout_seconds": e.timeout_seconds,
            },
        )

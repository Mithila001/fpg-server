from __future__ import annotations

from time import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.services.buildable_space_manager import run_buildable_space_pipeline
from app.util.unit_converter import converter_cm_to_unit, converter_unit_to_meters


_last_buildable_space_request: dict[str, float] = {}
_rate_limit_seconds = 2

router = APIRouter(prefix="/algorithms", tags=["algorithms"])


class CoordinatePayload(BaseModel):
    x: float
    y: float


class RoadConnectedPayload(BaseModel):
    segment: list[CoordinatePayload] = Field(default_factory=list)
    roadType: str | None = None


class BuildableSpaceRequest(BaseModel):
    area: float
    segmentsCoordinates: list[CoordinatePayload] = Field(min_length=3)
    roadConnected: list[RoadConnectedPayload] = Field(default_factory=list)
    min_width: float = 100
    min_height: float = 100
    should_plot: bool = False


class RectanglePayload(BaseModel):
    vertices: list[CoordinatePayload]
    width: float
    height: float
    area: float


class BuildableSpaceResponse(BaseModel):
    status: str
    message: str
    buildable_rectangle: RectanglePayload | None = None
    shrunk_boundary: list[CoordinatePayload] | None = None
    metadata: dict[str, Any] | None = None


@router.post("/buildable-space", response_model=BuildableSpaceResponse)
def get_buildable_space(request: Request, body: BuildableSpaceRequest):
    """Compute usable land and best fitting rectangle from API-provided land geometry."""
    client_ip = request.client.host if request.client else "unknown"
    now = time()
    last_call = _last_buildable_space_request.get(client_ip, 0)
    elapsed = now - last_call

    if elapsed < _rate_limit_seconds:
        retry_after = _rate_limit_seconds - elapsed
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {retry_after:.1f} seconds.",
            headers={"Retry-After": str(int(retry_after) + 1)},
        )

    _last_buildable_space_request[client_ip] = now

    land_payload = converter_cm_to_unit({
        "area": body.area,
        "segmentsCoordinates": [point.model_dump() for point in body.segmentsCoordinates],
        "roadConnected": [road.model_dump() for road in body.roadConnected],
    })

    payload = run_buildable_space_pipeline(
        land_data=land_payload,
        min_width=converter_cm_to_unit(body.min_width),
        min_height=converter_cm_to_unit(body.min_height),
        should_plot=body.should_plot,
    )
    return BuildableSpaceResponse(**converter_unit_to_meters(payload))

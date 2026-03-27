from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from time import time

from app.services.algorithm_manager import run_layout_pipeline
# from app.util.logger import SystemLogger

# In-memory per-client rate limit tracker (simple, single-process)
_last_format_request: dict[str, float] = {}
_rate_limit_seconds = 2


class PointResponse(BaseModel):
    x: float
    y: float


class WallSegmentResponse(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class RoomCenter(BaseModel):
    name: str
    type: str
    center: PointResponse


class OpeningSegmentResponse(BaseModel):
    room_name: str
    room_type: str
    opening_type: str
    side: str
    x1: float
    y1: float
    x2: float
    y2: float


class FormatterResponse(BaseModel):
    status: str
    message: str
    walls: List[WallSegmentResponse]
    rooms: List[RoomCenter]
    openings: List[OpeningSegmentResponse]


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

    # TODO : Currently not working due to formatting update.
    payload = run_layout_pipeline(use_optuna=True, verbose=False)

    walls = [WallSegmentResponse(**wall) for wall in payload.get("walls", [])]
    rooms = [
        RoomCenter(
            name=room.get("name", ""),
            type=room.get("type", ""),
            center=PointResponse(**room.get("center", {"x": 0.0, "y": 0.0})),
        )
        for room in payload.get("rooms", [])
    ]
    openings = [OpeningSegmentResponse(**opening) for opening in payload.get("openings", [])]

    return FormatterResponse(
        status=str(payload.get("status", "UNKNOWN")),
        message=str(payload.get("message", "")),
        walls=walls,
        rooms=rooms,
        openings=openings,
    )

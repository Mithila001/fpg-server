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


class FormatterResponse(BaseModel):
    status: str
    message: str
    walls: List[WallSegmentResponse]
    compact_by_room: dict[str, CompactRoomResponse]


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
    return FormatterResponse(**payload)

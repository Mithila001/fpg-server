from __future__ import annotations

from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.algorithm_manager import run_layout_pipeline


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


class FormatterResponse(BaseModel):
    status: str
    message: str
    walls: List[WallSegmentResponse]
    rooms: List[RoomCenter]


router = APIRouter(prefix="/algorithms", tags=["algorithms"])


@router.get("/format", response_model=FormatterResponse)
def get_formatted_layout():
    """Run the DB-backed solver and return post-processed wall layout payload."""
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

    return FormatterResponse(
        status=str(payload.get("status", "UNKNOWN")),
        message=str(payload.get("message", "")),
        walls=walls,
        rooms=rooms,
    )

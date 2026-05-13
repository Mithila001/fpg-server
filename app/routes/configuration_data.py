from __future__ import annotations

from fastapi import APIRouter

from app.types.room_size_constraint import RoomSizeConstraint as RoomSizeType
from app.util.algorithm_manager.load_server_side_data import load_server_side_data

router = APIRouter(prefix="/algorithms", tags=["algorithms"])


@router.get("/room-size-constraints", response_model=list[RoomSizeType])
def get_room_size_constraints() -> list[RoomSizeType]:
    _, size_constraints, _ = load_server_side_data()
    return size_constraints

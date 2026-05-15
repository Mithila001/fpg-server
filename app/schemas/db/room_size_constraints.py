from __future__ import annotations
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel


class RoomSizeConstraintBase(SQLModel):
    """Shared properties of a room size constraint."""

    type: str
    size: Optional[str] = None
    min_w: Optional[float] = None
    max_w: Optional[float] = None
    min_h: Optional[float] = None
    max_h: Optional[float] = None
    max_area: Optional[float] = None
    min_area: Optional[float] = None
    preset_id: Optional[str] = None


class RoomSizeConstraintCreate(RoomSizeConstraintBase):
    """Properties required when creating a new constraint."""
    ...


class RoomSizeConstraintRead(RoomSizeConstraintBase):
    """Properties returned in API responses."""

    id: int
    last_updated: datetime

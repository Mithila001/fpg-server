from __future__ import annotations
from datetime import date
from typing import List, Optional

from sqlmodel import SQLModel


class RoomRelationsConstraintBase(SQLModel):
    """Shared properties for a room relations constraint."""

    room_type: str
    related_room: Optional[List[str]] = None


class RoomRelationsConstraintCreate(RoomRelationsConstraintBase):
    """Fields required when inserting a new constraint."""
    ...


class RoomRelationsConstraintRead(RoomRelationsConstraintBase):
    """Fields returned in read operations."""

    id: int
    last_updated: date

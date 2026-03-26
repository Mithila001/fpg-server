from __future__ import annotations

from typing import List, Optional

from sqlmodel import SQLModel


class RoomRelationsConstraint(SQLModel):
    """Local relation-constraint type for floor-plan generator."""

    room_type: str
    related_room: Optional[List[str]] = None
    constraint_level: Optional[str] = None

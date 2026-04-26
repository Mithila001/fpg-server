from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel


class RoomRelationsConstraint(BaseModel):
    id: Optional[int] = None
    room_type: str
    related_room: Optional[List[str]] = None
    constraint_level: Optional[str] = None
    last_updated: Optional[date] = None

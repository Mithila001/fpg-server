from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class RoomSizeConstraint(BaseModel):
    id: Optional[int] = None
    type: str
    min_w: Optional[float] = None
    max_w: Optional[float] = None
    min_h: Optional[float] = None
    max_h: Optional[float] = None
    max_area: Optional[float] = None
    min_area: Optional[float] = None
    preset_id: Optional[str] = None
    last_updated: Optional[datetime] = None

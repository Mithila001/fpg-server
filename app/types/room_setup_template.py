from typing import Any, Optional
from pydantic import BaseModel


class RoomSetupTemplate(BaseModel):
    id: Optional[int] = None
    name: str
    data: list[dict[str, Any]]

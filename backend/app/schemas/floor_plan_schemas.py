from typing import List, Optional
from pydantic import BaseModel, Field


class RoomSpec(BaseModel):
    name: str = Field(..., description="Room display name, e.g. 'Living Room'.")
    type: str = Field(..., description="Room type key, e.g. 'LivingRoom', 'Bedroom'.")
    min_w: int = Field(..., description="Minimum width (grid units).")
    min_h: int = Field(..., description="Minimum height (grid units).")
    max_w: int = Field(..., description="Maximum width (grid units).")
    max_h: int = Field(..., description="Maximum height (grid units).")


class FloorPlanRequest(BaseModel):
    width: int = Field(100, description="Floor plan grid width.")
    height: int = Field(100, description="Floor plan grid height.")
    rooms_data: Optional[List[RoomSpec]] = Field(
        None,
        description=(
            "Room specifications. If omitted, the default rooms from config are used."
        ),
    )


class RoomResult(BaseModel):
    name: str
    type: str
    x: int
    y: int
    w: int
    h: int
    x_end: int
    y_end: int
    area: int


class FloorPlanResponse(BaseModel):
    solved: bool = Field(..., description="True if the solver found a valid layout.")
    rooms: List[RoomResult] = Field(default_factory=list)
    error: Optional[str] = Field(None, description="Error message if generation failed.")

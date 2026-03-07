from typing import List, Optional, Tuple
from pydantic import BaseModel, Field


Coordinate = Tuple[float, float]


class UsableLandRequest(BaseModel):
    vertices: List[Coordinate] = Field(
        ...,
        description="Ordered list of (x, y) vertices defining the land polygon.",
        examples=[[(15.0, 1.5), (16.5, 9.0), (10.5, 12.3), (3.9, 10.2)]],
    )
    offsets: List[float] = Field(
        ...,
        description="Per-edge setback distances. Must have the same length as vertices.",
        examples=[[1.0, 0.5, 0.5, 2.0]],
    )


class UsableLandResponse(BaseModel):
    buildable_vertices: List[Coordinate] = Field(
        ..., description="Vertices of the computed buildable polygon after setbacks."
    )
    error: Optional[str] = Field(None, description="Error message if algorithm failed.")


class UsableLandMockResponse(BaseModel):
    results: List[UsableLandResponse]
    total: int

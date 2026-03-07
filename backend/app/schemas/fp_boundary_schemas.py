from typing import List, Optional, Tuple
from pydantic import BaseModel, Field


Coordinate = Tuple[float, float]


class FPBoundaryRequest(BaseModel):
    polygon_coordinates: List[Coordinate] = Field(
        ...,
        description="Ordered list of (x, y) vertices defining the land polygon.",
        examples=[[(15.0, 1.5), (16.5, 9.0), (10.5, 12.3), (3.9, 10.2)]],
    )
    min_width: float = Field(5.0, description="Minimum acceptable rectangle width.")
    min_height: float = Field(0.5, description="Minimum acceptable rectangle height.")


class FPBoundaryResponse(BaseModel):
    final_polygon: List[Coordinate] = Field(
        ..., description="Transformed original polygon in world coordinates."
    )
    rect_parallel: List[Coordinate] = Field(
        ..., description="Largest rectangle aligned parallel to the first edge."
    )
    rect_perpendicular: List[Coordinate] = Field(
        ..., description="Largest rectangle aligned perpendicular to the first edge."
    )
    error: Optional[str] = Field(None, description="Error message if algorithm failed.")


class FPBoundaryMockResponse(BaseModel):
    results: List[FPBoundaryResponse]
    total: int

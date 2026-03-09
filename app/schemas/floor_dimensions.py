# F:\OnGoinProject\House Plane Generator Projects\house-plan-generator\backend\app\schemas\floor_dimensions.py

from pydantic import BaseModel
from typing import Literal

class FloorDimensionsIn(BaseModel):
    """
    Schema for the input dimensions and area size.
    'double' in Python (and Pydantic) is represented by 'float'.
    """
    front: float
    back: float
    left: float
    right: float
    areaSize: float

    # # Optional: Add validation to ensure all values are positive
    # class Config:
    #     schema_extra = {
    #         "example": {
    #             "front": 10.5,
    #             "back": 10.5,
    #             "left": 8.0,
    #             "right": 8.0,
    #             "areaSize": 84.0
    #         }
    #     }
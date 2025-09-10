from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel, Field
from ..services.layout_solver import solve_layout, Room, Rectangle

# We'll define the schemas for the request and response here for clarity
# These are a little different from the frontend schemas as they're for the API
# and don't need things like the 'id' field in the request.
class RoomIn(BaseModel):
    width: int = Field(..., gt=0, description="The width of the room.")
    height: int = Field(..., gt=0, description="The height of the room.")

class RoomOut(BaseModel):
    id: int
    width: int
    height: int
    x: int
    y: int

class Boundary(BaseModel):
    width: int
    height: int

class LayoutRequest(BaseModel):
    boundary: Boundary
    rooms: List[RoomIn]

# Create a new router instance
router = APIRouter(prefix="/layout", tags=["Layout"])

@router.post("/generate", response_model=List[RoomOut])
async def generate_floor_plan(request: LayoutRequest):
    """
    Generates a floor plan by automatically arranging rooms
    within a given boundary using a backtracking algorithm.
    """
    # Create the Room objects for our solver, adding a unique ID
    rooms_for_solver = [
        Room(
            id=i, 
            width=r.width, 
            height=r.height
        ) for i, r in enumerate(request.rooms)
    ]
    
    # Create the boundary rectangle
    boundary = Rectangle(
        x=0, 
        y=0, 
        width=request.boundary.width, 
        height=request.boundary.height
    )

    # Solve the layout!
    placed_rooms = solve_layout(rooms_for_solver, boundary)

    if placed_rooms is None:
        raise HTTPException(status_code=400, detail="Could not find a valid layout for the given rooms and boundary.")
    
    # Convert the placed rooms back to our response schema
    return placed_rooms
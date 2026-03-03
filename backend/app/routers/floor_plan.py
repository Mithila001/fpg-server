from fastapi import APIRouter
from app.algorithms.floor_plan_generator import FloorPlanGenerator
from app.algorithms.floor_plan_generator.config import (
    DEFAULT_ROOMS_DATA,
    FLOOR_WIDTH,
    FLOOR_HEIGHT,
)
from app.schemas.floor_plan_schemas import (
    FloorPlanRequest,
    FloorPlanResponse,
    RoomResult,
)

router = APIRouter(prefix="/floor-plan", tags=["Floor Plan Generator"])


@router.post("/generate", response_model=FloorPlanResponse)
def generate_floor_plan(request: FloorPlanRequest):
    """
    Generate a floor plan layout using CP-SAT constraint solving.

    - `width` / `height`: grid dimensions of the floor
    - `rooms_data`: list of room specs; if omitted, default rooms from config are used
    """
    try:
        rooms_data = (
            [r.model_dump() for r in request.rooms_data]
            if request.rooms_data
            else DEFAULT_ROOMS_DATA
        )
        generator = FloorPlanGenerator(
            width=request.width,
            height=request.height,
            rooms_data=rooms_data,
        )
        solved = generator.generate()

        if not solved:
            return FloorPlanResponse(solved=False, error="No feasible solution found.")

        solution = generator.get_solution()
        rooms = [RoomResult(**r) for r in solution]
        return FloorPlanResponse(solved=True, rooms=rooms)

    except Exception as exc:
        return FloorPlanResponse(solved=False, error=str(exc))


@router.post("/generate-mock", response_model=FloorPlanResponse)
def generate_floor_plan_mock():
    """
    Generate a floor plan using the default configuration (DEFAULT_ROOMS_DATA,
    FLOOR_WIDTH x FLOOR_HEIGHT).
    """
    try:
        generator = FloorPlanGenerator(
            width=FLOOR_WIDTH,
            height=FLOOR_HEIGHT,
            rooms_data=DEFAULT_ROOMS_DATA,
        )
        solved = generator.generate()

        if not solved:
            return FloorPlanResponse(solved=False, error="No feasible solution found.")

        solution = generator.get_solution()
        rooms = [RoomResult(**r) for r in solution]
        return FloorPlanResponse(solved=True, rooms=rooms)

    except Exception as exc:
        return FloorPlanResponse(solved=False, error=str(exc))

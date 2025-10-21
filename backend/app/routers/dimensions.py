# F:\OnGoinProject\House Plane Generator Projects\house-plan-generator\backend\app\routers\dimensions.py

from fastapi import APIRouter
from ..schemas.floor_dimensions import FloorDimensionsIn

# Create a new router instance with a prefix
router = APIRouter(prefix="/dimensions", tags=["Dimensions"])

@router.post("/process", response_model=str)
async def process_floor_dimensions(dimensions: FloorDimensionsIn):
    """
    Receives front, back, left, right, and areaSize inputs.
    For now, it simply validates and returns a success message.
    """
    
    # NOTE: The data in the 'dimensions' variable (e.g., dimensions.front, dimensions.areaSize)
    # is already guaranteed to be a valid float by Pydantic.
    
    # In the future, you would add your core logic here:
    # 1. Save data to the database using CRUD functions.
    # 2. Start a background task for layout generation.
    # 3. Perform immediate validation checks (e.g., area consistency).
    
    # Returning a simple success string as requested
    return "Success: Dimensions received and validated."
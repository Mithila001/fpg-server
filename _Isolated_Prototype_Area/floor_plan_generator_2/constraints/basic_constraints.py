from typing import List
from ..models.room import Room

def add_basic_constraints(model, rooms: List[Room]):
    """
    Args:
        model: CpModel instance
        rooms: List of Room objects
    """
    # Extract intervals from the room objects for NoOverlap
    x_intervals = [r.x_interval for r in rooms]
    y_intervals = [r.y_interval for r in rooms]
    model.AddNoOverlap2D(x_intervals, y_intervals)
    
    for r in rooms:
        # Endpoint definitions (using object attributes)
        model.Add(r.x + r.w == r.x_end) # type: ignore
        model.Add(r.y + r.h == r.y_end) # type: ignore
        
        # Aspect ratio constraints
        model.Add(r.w <= 2 * r.h) # type: ignore
        model.Add(r.h <= 2 * r.w) # type: ignore
    
    print("Added basic constraints using Room objects")
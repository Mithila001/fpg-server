from typing import List, Optional, Sequence

from app.algorithms.floor_plan_generator import FloorPlanGenerator
from app.algorithms.floor_plan_generator.types.room import (
    RoomData,
    ConfigData,
    FpgRequirements,
)
from app.algorithms.floor_plan_generator.config import (
    FLOOR_WIDTH,
    FLOOR_HEIGHT,
    MIN_COVERAGE,
)

from sqlmodel import Session
from app.core.database import engine
from app.crud import (
    room_size_constraint as room_size_constraint_crud,
    room_setup_template as room_setup_template_crud,
    room_relations_constraint as room_relations_constraint_crud,
)
from app.models.room_size_constraint import RoomSizeConstraint


def _normalize_requirements(
    rooms: List[RoomData],
    constraints: Sequence[RoomSizeConstraint],
) -> List[RoomData]:
    """Normalize room dimensions based on database constraint rules.
    
    This function validates and normalizes room data against the database-defined
    size constraints:
    - Ensures min_w <= max_w and min_h <= max_h
    - Clamps room dimensions within constraint bounds
    - Validates that constraint values are logically consistent
    
    Args:
        rooms: List of RoomData objects to normalize
        constraints: Sequence of RoomSizeConstraint objects from database
    
    Returns:
        Normalized list of RoomData objects
    
    Raises:
        ValueError: If constraint values are invalid or inconsistent
    """
    constraints_by_type = {c.type: c for c in constraints}
    normalized: List[RoomData] = []
    
    for room in rooms:
        constraint = constraints_by_type.get(room.type)
        
        if not constraint:
            raise ValueError(
                f"ERROR: Room type '{room.type}' has no constraint record in database"
            )
        
        # Validate constraint consistency
        if constraint.min_w is not None and constraint.max_w is not None:
            if constraint.min_w > constraint.max_w:
                raise ValueError(
                    f"ERROR: Invalid constraint for '{room.type}': min_w ({constraint.min_w}) "
                    f"exceeds max_w ({constraint.max_w})"
                )
        
        if constraint.min_h is not None and constraint.max_h is not None:
            if constraint.min_h > constraint.max_h:
                raise ValueError(
                    f"ERROR: Invalid constraint for '{room.type}': min_h ({constraint.min_h}) "
                    f"exceeds max_h ({constraint.max_h})"
                )
        
        # Clamp room dimensions within constraint bounds
        min_w = max(room.min_w, int(constraint.min_w)) if constraint.min_w is not None else room.min_w
        min_h = max(room.min_h, int(constraint.min_h)) if constraint.min_h is not None else room.min_h
        max_w = min(room.max_w, int(constraint.max_w)) if constraint.max_w is not None else room.max_w
        max_h = min(room.max_h, int(constraint.max_h)) if constraint.max_h is not None else room.max_h
        
        # Ensure final mins don't exceed maxes after clamping
        if min_w > max_w:
            raise ValueError(
                f"ERROR: After normalization, room '{room.name}' ({room.type}) has "
                f"min_w ({min_w}) > max_w ({max_w})"
            )
        if min_h > max_h:
            raise ValueError(
                f"ERROR: After normalization, room '{room.name}' ({room.type}) has "
                f"min_h ({min_h}) > max_h ({max_h})"
            )
        
        normalized.append(
            RoomData(
                name=room.name,
                type=room.type,
                min_w=min_w,
                min_h=min_h,
                max_w=max_w,
                max_h=max_h,
            )
        )
    
    return normalized


def DEV_RunFPG() -> None:
    """Development function that retrieves database records and runs the floor plan generator.
    
    This function:
    1. Retrieves room setup templates from the database
    2. Retrieves room size constraints from the database
    3. Retrieves room relations constraints from the database
    4. Structures the data into FpgRequirements format
    5. Initializes FloorPlanGenerator
    6. Calls generate() and prints results
    """
    
    with Session(engine) as session:
        # Retrieve all database records
        templates = room_setup_template_crud.get_all(session)
        size_constraints = room_size_constraint_crud.get_all(session)
        relation_constraints = room_relations_constraint_crud.get_all(session)
        
        print(f"Retrieved {len(templates)} templates")
        print(f"Retrieved {len(size_constraints)} size constraints")
        print(f"Retrieved {len(relation_constraints)} relation constraints")
        
        # If no templates, exit early
        if not templates:
            print("No room setup templates found in database")
            return
        
        # Use the first template as the basis
        template = templates[0]
        print(f"\nUsing template: {template.name}")
        
        # Create a lookup map for size constraints by room type
        size_constraints_by_type = {c.type: c for c in size_constraints}
        
        # Build RoomData list from template data
        rooms: List[RoomData] = []
        if template.data:
            for entry in template.data:
                room_type = entry.get("type", "")
                room_name = entry.get("name") or entry.get("id") or room_type
                
                # Look up size constraints for this room type
                constraint = size_constraints_by_type.get(room_type)
                
                if not constraint:
                    raise ValueError(
                        f"ERROR: Room type '{room_type}' has no size constraints defined in database. "
                        f"Please add a room size constraint record for this type before proceeding."
                    )
                
                # All constraint values must be explicitly set
                if constraint.min_w is None:
                    raise ValueError(
                        f"ERROR: Room size constraint for '{room_type}' is missing min_w value"
                    )
                if constraint.min_h is None:
                    raise ValueError(
                        f"ERROR: Room size constraint for '{room_type}' is missing min_h value"
                    )
                if constraint.max_w is None:
                    raise ValueError(
                        f"ERROR: Room size constraint for '{room_type}' is missing max_w value"
                    )
                if constraint.max_h is None:
                    raise ValueError(
                        f"ERROR: Room size constraint for '{room_type}' is missing max_h value"
                    )
                
                rooms.append(
                    RoomData(
                        name=room_name,
                        type=room_type,
                        min_w=int(constraint.min_w),
                        min_h=int(constraint.min_h),
                        max_w=int(constraint.max_w),
                        max_h=int(constraint.max_h),
                    )
                )
        
        print(f"Created {len(rooms)} RoomData objects")
        for room in rooms:
            print(f"  - {room.name} ({room.type}): {room.min_w}-{room.max_w} x {room.min_h}-{room.max_h}")
        
        # Normalize rooms based on database constraint rules
        print("\nNormalizing rooms against database constraints...")
        rooms = _normalize_requirements(rooms, size_constraints)
        
        print(f"Normalized {len(rooms)} RoomData objects")
        for room in rooms:
            print(f"  - {room.name} ({room.type}): {room.min_w}-{room.max_w} x {room.min_h}-{room.max_h}")
        
        # Create ConfigData
        config = ConfigData(
            min_coverage=MIN_COVERAGE,
            max_aspect_ratio=16.0,
            min_aspect_ratio=0.0,
            floor_plan_width=FLOOR_WIDTH,
            floor_plan_height=FLOOR_HEIGHT,
        )
        
        # Create FpgRequirements
        requirements = FpgRequirements(rooms=rooms, config=config)
        
        print(f"\nCreated FpgRequirements with {len(requirements.rooms)} rooms")
        print(f"Floor dimensions: {config.floor_plan_width} x {config.floor_plan_height}")
        
        # Initialize FloorPlanGenerator
        generator = FloorPlanGenerator(requirements)
        print("FloorPlanGenerator initialized")
        
        # Generate floor plan
        print("\nCalling generate()...")
        solved = generator.generate()
        
        if solved:
            print("✓ Floor plan generated successfully!")
            solution = generator.get_solution()
            print(f"\nSolution with {len(solution)} rooms:")
            for room_result in solution:
                print(f"  - {room_result['name']} ({room_result['type']})")
                print(f"    Position: ({room_result['x']}, {room_result['y']})")
                print(f"    Size: {room_result['w']} x {room_result['h']}")
                print(f"    Area: {room_result['area']}")
        else:
            print("✗ Floor plan generation failed - no solution found")

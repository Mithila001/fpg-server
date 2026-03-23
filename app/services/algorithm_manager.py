from typing import List, Sequence

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
from app.algorithms.floor_plan_generator.fpg_score import score_layout

from sqlmodel import Session
from app.core.database import engine
from app.crud import (
    room_size_constraint as room_size_constraint_crud,
    room_setup_template as room_setup_template_crud,
    room_relations_constraint as room_relations_constraint_crud,
)
from app.models.room_size_constraint import RoomSizeConstraint


# Fallback room dimension used when a room_size_constraints column is NULL.
DEFAULT_ROOM_DIMENSION = 1000


def _normalize_requirements(
    rooms: List[RoomData],
    constraints: Sequence[RoomSizeConstraint],
) -> List[RoomData]:
    """Normalize room dimensions from DB constraints with simple defaults.

    For each room type, use the DB value when present; otherwise use 10.
    """
    constraints_by_type = {c.type: c for c in constraints}
    normalized: List[RoomData] = []
    
    for room in rooms:
        constraint = constraints_by_type.get(room.type)
        
        if not constraint:
            raise ValueError(
                f"ERROR: Room type '{room.type}' has no constraint record in database"
            )

        min_w = int(constraint.min_w) if constraint.min_w is not None else 10
        min_h = int(constraint.min_h) if constraint.min_h is not None else 10
        max_w = int(constraint.max_w) if constraint.max_w is not None else 1000
        max_h = int(constraint.max_h) if constraint.max_h is not None else 1000
        
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


def DEV_RUN() -> None:
    """Development function that retrieves database records and runs the floor plan generator.
    
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
        
        # Build RoomData list from template data
        rooms: List[RoomData] = []
        if template.data:
            for entry in template.data:
                room_type = entry.get("type", "")
                room_name = entry.get("name") or entry.get("id") or room_type
                
                rooms.append(
                    RoomData(
                        name=room_name,
                        type=room_type,
                        min_w=1,
                        min_h=1,
                        max_w=1,
                        max_h=1,
                    )
                )
        
        print(f"Created {len(rooms)} RoomData objects")
        for room in rooms:
            print(f"  - {room.name} ({room.type}): {room.min_w}-{room.max_w} * {room.min_h}-{room.max_h}")
        
        # Normalize rooms based on database constraint rules
        print("\nNormalizing rooms against database constraints...")
        rooms = _normalize_requirements(rooms, size_constraints)
        
        print(f"Normalized {len(rooms)} RoomData objects")
        for room in rooms:
            print(f"  - {room.name} ({room.type}): Min W: {room.min_w} - Max W: {room.max_w} * Min H: {room.min_h} - Max H: {room.max_h}")
        
        # Create ConfigData
        config = ConfigData(
            min_coverage=MIN_COVERAGE,
            max_aspect_ratio=16.0,
            min_aspect_ratio=0.0,
            floor_plan_width=FLOOR_WIDTH,
            floor_plan_height=FLOOR_HEIGHT,
        )
        
        # Create FpgRequirements with relation constraints
        print(f"Floor dimensions: {config.floor_plan_width} x {config.floor_plan_height}")
        requirements = FpgRequirements(
            rooms=rooms,
            config=config,
            relation_constraints=relation_constraints
        )
        RunFPG(requirements)
        
        
            
            
def RunFPG(requirements: FpgRequirements) -> None:
    
    print(f"\nCreated FpgRequirements with {len(requirements.rooms)} rooms")
    print(f"\nRequirements {requirements}\n\n")
    
    # Initialize FloorPlanGenerator
    generator = FloorPlanGenerator(requirements)
    print("FloorPlanGenerator initialized")
    
    # Generate floor plan
    print("\nCalling generate()...")
    solved = generator.generate()
    
    if solved:
        print("✓ Floor plan generated successfully!")
        solution = generator.get_solution()
        score_report = score_layout(solution, requirements)

        print(f"\nSolution with {len(solution)} rooms:")
        for room_result in solution:
            print(f"  - {room_result['name']} ({room_result['type']})")
            print(f"    Position: ({room_result['x']}, {room_result['y']})")
            print(f"    Size: {room_result['w']} x {room_result['h']}")
            print(f"    Area: {room_result['area']}")

        print("\nScore Report:")
        print(f"  - Valid: {score_report.valid}")
        print(f"  - Total Score: {score_report.total_score}")
        print(f"  - Component Scores: {score_report.component_scores}")
        if score_report.hard_violations:
            print("  - Hard Violations:")
            for violation in score_report.hard_violations:
                print(f"    * {violation}")
        print(f"  - Diagnostics: {score_report.diagnostics}")
            
        print("\nRaw Solution:")
        print(solution)
    else:
        print("✗ Floor plan generation failed - no solution found")
    
    
def OptunaEntry():
    print("Optuna Entry")
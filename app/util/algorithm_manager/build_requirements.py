import math
from typing import Tuple, List
from app.algorithms.fpg_rooms.types.room import ConfigData, FpgRequirements
from app.core.fpg_rooms.config_fpg import (
    DEFAULT_ASPECT_RATIO_MAX,
    DEFAULT_ASPECT_RATIO_MIN,
    DEFAULT_HALLWAY_COUNT,
    ENVELOPE_APPLY_SIDES,
    ENVELOPE_ENABLED,
    ENVELOPE_EXCLUDE_TYPES,
    ENVELOPE_MAX_GAP,
    ENVELOPE_MIN_GAP,
    MIN_COVERAGE,
    MIN_FLOOR_AREA_BUFFER
)
#from app.models.room_size_constraint import RoomSizeConstraint
from app.schemas.db.room_setup_template import RoomSetupTemplateBase
from app.util.constraint_pruner import prune_room_relations_constraints_by_template
from app.util.room_requirements import normalize_db_data_requirements
from app.util.algorithm_manager.build_rooms_from_template import (
    build_rooms_from_template,
)
from app.util.algorithm_manager.load_server_side_data import load_server_side_data


def build_requirements(
    floor_width: float,
    floor_height: float,
    room_template: RoomSetupTemplateBase,
) -> FpgRequirements:
    """Build FpgRequirements from template, loading and pruning server-side constraints.

    This function now handles all data loading and constraint pruning internally.
    Raises exceptions if any step fails (no silent defaults).
    """
    # print parameter values for debugging
    print(f"\n\nBuilding requirements with floor_width: {floor_width}, floor_height: {floor_height}, room_template: {room_template}")
    
    try:
        _, size_constraints, relation_constraints = load_server_side_data()
        print(f"\nSize Constraints: {size_constraints}")
    except Exception as exc:
        raise Exception(f"Failed to load server-side constraints: {exc}") from exc
    
    floor_width, floor_height = _calculate_suitable_floor_dimensions(
        floor_width=floor_width,
        floor_height=floor_height,
        room_template_data=room_template.data,
        size_constraints=size_constraints,
        buffer=MIN_FLOOR_AREA_BUFFER
    )

    try:
        relation_constraints, prune_error = (
            prune_room_relations_constraints_by_template(
                room_template=room_template,
                room_relations_constraints=relation_constraints,
            )
        )
        if prune_error:
            raise Exception(f"Failed to prune relation constraints: {prune_error}")
    except Exception as exc:
        raise Exception(f"Failed to prune room relations constraints: {exc}") from exc
    # print(f"\n\n Load Size Constraints : {size_constraints} \n\n")
    rooms = build_rooms_from_template(room_template)
    normalized_rooms = normalize_db_data_requirements(rooms, size_constraints)

    config = ConfigData(
        min_coverage=MIN_COVERAGE,
        max_aspect_ratio=DEFAULT_ASPECT_RATIO_MAX,
        min_aspect_ratio=DEFAULT_ASPECT_RATIO_MIN,
        floor_plan_width=floor_width,
        floor_plan_height=floor_height,
        hallway_count=DEFAULT_HALLWAY_COUNT,
        envelope_enabled=ENVELOPE_ENABLED,
        envelope_min_gap=ENVELOPE_MIN_GAP,
        envelope_max_gap=ENVELOPE_MAX_GAP,
        envelope_exclude_types=ENVELOPE_EXCLUDE_TYPES,
        envelope_apply_sides=ENVELOPE_APPLY_SIDES,
    )

    return FpgRequirements(
        rooms=normalized_rooms,
        config=config,
        relation_constraints=list(relation_constraints),
    )

def _calculate_suitable_floor_dimensions(
    floor_width: float,
    floor_height: float,
    room_template_data: List[dict],
    size_constraints: List[any], # Using any for brevity; replace with RoomSizeConstraint
    buffer: float
) -> Tuple[float, float]:
    """
    Calculates optimized floor dimensions based on strict area requirements and 
    aspect ratio constraints.
    """
    
    # Check if template data exists
    if not room_template_data:
        raise ValueError("Room template data is empty or missing.")

    # 1. Calculate min and max areas from template
    total_min_area = 0
    total_max_area = 0
    
    # Create a lookup for performance
    constraint_map = {c.type: c for c in size_constraints}
    
    for room in room_template_data:
        r_type = room.get('type')
        if not r_type:
             raise ValueError(f"Room entry missing 'type' key: {room}")
             
        constraint = constraint_map.get(r_type)
        
        # ERROR: Throw error if size constraint for a room type is missing
        if not constraint:
            raise ValueError(f"Missing size constraints for room type: '{r_type}'")
            
        total_min_area += constraint.min_area
        total_max_area += constraint.max_area

    current_floor_area = floor_width * floor_height
    required_min_total = total_min_area + buffer
    required_max_total = total_max_area + buffer

    # 2. Check if minimum area fits
    if required_min_total > current_floor_area:
        raise ValueError(
            f"Insufficient Floor Space: Required minimum {required_min_total} "
            f"exceeds available {current_floor_area}."
        )

    # 3. Geometric Logic: Find the largest rectangle with 10:16 ratio
    # W:H = 10:16 -> W = 10k, H = 16k -> Area = 160k^2
    k = math.sqrt(required_max_total / 160)
    target_w = 10 * k
    target_h = 16 * k

    # Logic for fitting into given floor dimensions
    if target_w <= floor_width and target_h <= floor_height:
        # Fits perfectly with 10:16 ratio
        floor_plan_width, floor_plan_height = target_w, target_h
    else:
        # Use max width as rectangle width and calculate available height needed for max area
        floor_plan_width = floor_width
        needed_h = required_max_total / floor_plan_width
        
        if needed_h <= floor_height:
            floor_plan_height = needed_h
        else:
            # Fallback to provided floor dimensions if max area doesn't fit the logic
            floor_plan_width = floor_width
            floor_plan_height = floor_height

    # 4. Aspect Ratio Validation (Must not be higher than 1:2)
    # Higher than 1:2 means the ratio of long-side to short-side is > 2.0
    if floor_plan_width > 0 and floor_plan_height > 0:
        max_dim = max(floor_plan_width, floor_plan_height)
        min_dim = min(floor_plan_width, floor_plan_height)
        actual_ratio = max_dim / min_dim
        
        if actual_ratio > 2.0:
            raise ValueError(
                f"Invalid Floor Geometry: Aspect ratio {actual_ratio:.2f} is higher "
                f"than the 1:2 limit."
            )
    else:
        raise ValueError("Calculated floor dimensions must be greater than zero.")

    return floor_plan_width, floor_plan_height
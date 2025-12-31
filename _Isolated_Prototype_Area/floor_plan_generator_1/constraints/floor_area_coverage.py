"""
Area coverage constraints for floor plan generation.
Ensures rooms occupy a minimum percentage of available land.
"""

def add_minimum_area_coverage(model, all_vars, floor_width, floor_height, min_coverage=0.8):
    """
    Add constraint to ensure total room area meets minimum coverage.
    
    Args:
        model: CP-SAT model
        all_vars: Dictionary of room variables (from create_room_variables)
        floor_width: Total floor width
        floor_height: Total floor height
        min_coverage: Minimum coverage ratio (default 0.8 for 80%)
    """
    total_floor_area = floor_width * floor_height
    min_required_area = int(total_floor_area * min_coverage)

    # Collect the area variables that were created in create_room_variables
    room_areas = [vars_dict['area'] for vars_dict in all_vars.values()]
    model.Add(sum(room_areas) >= min_required_area)

    print(f"Added minimum area constraint: {min_required_area}/{total_floor_area} ({min_coverage*100}%)")

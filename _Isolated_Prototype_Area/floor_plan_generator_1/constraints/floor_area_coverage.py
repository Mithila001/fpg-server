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

    # Calculate area for each room (width * height)
    room_areas = []
    for room_name, vars_dict in all_vars.items():
        width_var = vars_dict['w']
        height_var = vars_dict['h']
        
        # Create intermediate variable for this room's area
        area_var = model.NewIntVar(0, floor_width * floor_height, f'{room_name}_area')
        model.AddMultiplicationEquality(area_var, [width_var, height_var])
        room_areas.append(area_var)
    
    # Sum of all room areas must be >= minimum required
    model.Add(sum(room_areas) >= min_required_area)

    print(f"Added minimum area constraint: {min_required_area}/{total_floor_area} ({min_coverage*100}%)")

"""
Creates all decision variables for rooms.
"""

def create_room_variables(model, rooms_data, land_width, land_height):
    """
    Create all variables for rooms (position, dimension, intervals).
    
    Parameters:
        model: CpModel instance
        rooms_data: List of room specifications
        land_width: Width of the land
        land_height: Height of the land
        
    Returns:
        all_vars: Dictionary of room variables
        x_intervals: List of x-interval variables
        y_intervals: List of y-interval variables
    """
    all_vars = {}
    x_intervals = []
    y_intervals = []
    VALUE_INCREMENT = 50  # Max extra size for room dimensions
    
    for room in rooms_data:
        name = room["name"]
        
        # Position Variables
        x = model.NewIntVar(0, land_width - room["min_w"], f'{name}_x')
        y = model.NewIntVar(0, land_height - room["min_h"], f'{name}_y')
        
        # Dimension Variables
        w = model.NewIntVar(room["min_w"], room["min_w"] + VALUE_INCREMENT, f'{name}_w')
        h = model.NewIntVar(room["min_h"], room["min_h"] + VALUE_INCREMENT, f'{name}_h')

        # Area
        area = model.NewIntVar(0, land_width * land_height, f'{name}_area')
        model.AddMultiplicationEquality(area, [w, h])

        # End Variables
        x_end = model.NewIntVar(0, land_width, f'{name}_x_end')
        y_end = model.NewIntVar(0, land_height, f'{name}_y_end')
        
        # Interval Variables
        x_interval = model.NewIntervalVar(x, w, x_end, f'{name}_x_interval')
        y_interval = model.NewIntervalVar(y, h, y_end, f'{name}_y_interval')
        
        x_intervals.append(x_interval)
        y_intervals.append(y_interval)
        
        # Store all variables
        all_vars[name] = {
            'x': x, 'y': y, 'w': w, 'h': h,
            'x_end': x_end, 'y_end': y_end,
            'area': area
        }
    
    return all_vars, x_intervals, y_intervals

"""
Basic geometric constraints: non-overlap and boundaries.
"""

def add_basic_constraints(model, all_vars, x_intervals, y_intervals):
    """
    Add basic constraints: non-overlap and end variable definitions.
    
    Parameters:
        model: CpModel instance
        all_vars: Dictionary of room variables
        x_intervals: List of x-interval variables
        y_intervals: List of y-interval variables
    """
    # Non-Overlap Constraint
    model.AddNoOverlap2D(x_intervals, y_intervals)
    
    # Define end variables for all rooms
    for room_name, vars_dict in all_vars.items():
        model.Add(vars_dict['x'] + vars_dict['w'] == vars_dict['x_end'])
        model.Add(vars_dict['y'] + vars_dict['h'] == vars_dict['y_end'])

"""
Basic geometric constraints: non-overlap, boundaries, and aspect ratios.
"""

def add_basic_constraints(model, all_vars, x_intervals, y_intervals):
    """
    Add basic constraints: non-overlap, end variable definitions, and aspect ratios.
    
    Parameters:
        model: CpModel instance
        all_vars: Dictionary of room variables
        x_intervals: List of x-interval variables
        y_intervals: List of y-interval variables
    """
    # Non-Overlap Constraint
    model.AddNoOverlap2D(x_intervals, y_intervals)
    
    # Define end variables and aspect ratio constraints for all rooms
    for room_name, vars_dict in all_vars.items():
        w = vars_dict['w']
        h = vars_dict['h']
        
        # End variable definitions
        model.Add(vars_dict['x'] + w == vars_dict['x_end'])
        model.Add(vars_dict['y'] + h == vars_dict['y_end'])
        
        # Aspect ratio constraints: prevent extremely elongated rooms
        # Ensure: 0.5 <= width/height <= 2.0
        # Which translates to: h/2 <= w <= 2*h AND w/2 <= h <= 2*w
        
        # Width should not be more than 2x height
        model.Add(w <= 2 * h)
        
        # Height should not be more than 2x width
        model.Add(h <= 2 * w)
        
        # This ensures rooms are roughly square to moderately rectangular
        # (ratio between 1:2 and 2:1)
    
    print("Added basic constraints (non-overlap, boundaries, aspect ratios)")

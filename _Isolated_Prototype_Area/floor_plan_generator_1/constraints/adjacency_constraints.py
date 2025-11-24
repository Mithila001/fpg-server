"""
Adjacency constraints between rooms.
"""

def add_adjacency_constraint(model, room1_vars, room2_vars, room1_name, room2_name):
    """
    Add complete adjacency constraint between two rooms with channeling.
    
    Parameters:
        model: CpModel instance
        room1_vars: Variables dictionary for room 1
        room2_vars: Variables dictionary for room 2
        room1_name: Name of room 1 (for variable naming)
        room2_name: Name of room 2 (for variable naming)
        
    Returns:
        Dictionary of boolean variables for touch directions
    """
    # Create boolean variables for each adjacency direction
    touch_right = model.NewBoolVar(f'{room1_name}_right_of_{room2_name}')
    touch_left = model.NewBoolVar(f'{room1_name}_left_of_{room2_name}')
    touch_top = model.NewBoolVar(f'{room1_name}_above_{room2_name}')
    touch_bottom = model.NewBoolVar(f'{room1_name}_below_{room2_name}')
    
    # TOUCH_RIGHT Channeling
    model.Add(room1_vars['x'] == room2_vars['x_end']).OnlyEnforceIf(touch_right)
    model.Add(room1_vars['x'] != room2_vars['x_end']).OnlyEnforceIf(touch_right.Not())
    
    # TOUCH_LEFT Channeling
    model.Add(room1_vars['x_end'] == room2_vars['x']).OnlyEnforceIf(touch_left)
    model.Add(room1_vars['x_end'] != room2_vars['x']).OnlyEnforceIf(touch_left.Not())
    
    # TOUCH_TOP Channeling
    model.Add(room1_vars['y'] == room2_vars['y_end']).OnlyEnforceIf(touch_top)
    model.Add(room1_vars['y'] != room2_vars['y_end']).OnlyEnforceIf(touch_top.Not())
    
    # TOUCH_BOTTOM Channeling
    model.Add(room1_vars['y_end'] == room2_vars['y']).OnlyEnforceIf(touch_bottom)
    model.Add(room1_vars['y_end'] != room2_vars['y']).OnlyEnforceIf(touch_bottom.Not())
    
    # At least ONE must be true
    model.AddBoolOr([touch_right, touch_left, touch_top, touch_bottom])
    
    # Perpendicular overlap constraints
    # Horizontal touching (left/right) needs vertical overlap
    model.Add(room1_vars['y'] < room2_vars['y_end']).OnlyEnforceIf(touch_right)
    model.Add(room2_vars['y'] < room1_vars['y_end']).OnlyEnforceIf(touch_right)
    model.Add(room1_vars['y'] < room2_vars['y_end']).OnlyEnforceIf(touch_left)
    model.Add(room2_vars['y'] < room1_vars['y_end']).OnlyEnforceIf(touch_left)
    
    # Vertical touching (top/bottom) needs horizontal overlap
    model.Add(room1_vars['x'] < room2_vars['x_end']).OnlyEnforceIf(touch_top)
    model.Add(room2_vars['x'] < room1_vars['x_end']).OnlyEnforceIf(touch_top)
    model.Add(room1_vars['x'] < room2_vars['x_end']).OnlyEnforceIf(touch_bottom)
    model.Add(room2_vars['x'] < room1_vars['x_end']).OnlyEnforceIf(touch_bottom)
    
    return {
        'right': touch_right,
        'left': touch_left,
        'top': touch_top,
        'bottom': touch_bottom
    }


def add_kitchen_living_adjacency(model, all_vars):
    """
    Specific constraint: Kitchen must be adjacent to Living Room.
    """
    touch_vars = add_adjacency_constraint(
        model,
        all_vars["Kitchen"],
        all_vars["Living Room"],
        "Kitchen",
        "LivingRoom"
    )
    return touch_vars

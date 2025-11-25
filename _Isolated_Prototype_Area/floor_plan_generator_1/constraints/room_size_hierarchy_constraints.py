"""
Room hierarchy constraints to maintain realistic relative sizes.
"""

def add_room_size_hierarchy(model, all_vars):
    """
    Enforce realistic size relationships between rooms.
    Living Room should be largest, bathroom smallest, etc.
    
    Args:
        model: CP-SAT model
        all_vars: Dictionary of room variables
    """
    # Create area variables for each room
    areas = {}
    for room_name, vars_dict in all_vars.items():
        area_var = model.NewIntVar(0, 10000, f'{room_name}_area')
        model.AddMultiplicationEquality(area_var, [vars_dict['w'], vars_dict['h']])
        areas[room_name] = area_var
    
    # Define hierarchy: Living Room > Bedroom > Kitchen > Bathroom
    if "Living Room" in areas and "Bedroom" in areas:
        model.Add(areas["Living Room"] >= areas["Bedroom"])
    
    if "Bedroom" in areas and "Kitchen" in areas:
        model.Add(areas["Bedroom"] >= areas["Kitchen"])
    
    if "Kitchen" in areas and "Bathroom" in areas:
        model.Add(areas["Kitchen"] >= areas["Bathroom"])
    
    print("Added room size hierarchy constraints")

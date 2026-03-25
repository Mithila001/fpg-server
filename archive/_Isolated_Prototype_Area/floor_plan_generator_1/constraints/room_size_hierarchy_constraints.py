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
    
    # Define hierarchy: Living Room > Bedroom > Kitchen > Bathroom
    if "Living Room" not in all_vars:
        return

    lr_area = all_vars["Living Room"]["area"]

    # Define the ranges for other rooms
    # We use: Room_Area * 100 to allow for "percentage" math with integers
    
    # 1. Bedroom: Should be 40% to 60% of Living Room
    if "Bedroom" in all_vars:
        br_area = all_vars["Bedroom"]["area"]
        model.Add(br_area * 100 >= lr_area * 40) # Min 40%
        model.Add(br_area * 100 <= lr_area * 60) # Max 60%

    # 2. Kitchen: Should be 60% to 80% of Living Room
    if "Kitchen" in all_vars:
        k_area = all_vars["Kitchen"]["area"]
        model.Add(k_area * 100 >= lr_area * 60) # Min 60%
        model.Add(k_area * 100 <= lr_area * 80) # Max 80%

    # 3. Bathroom: Should be 15% to 30% of Living Room
    if "Bathroom" in all_vars:
        ba_area = all_vars["Bathroom"]["area"]
        model.Add(ba_area * 100 >= lr_area * 15) # Min 15%
        model.Add(ba_area * 100 <= lr_area * 30) # Max 30%

    print("Added room size hierarchy constraints")

# from ortools.sat.python import cp_model
# import matplotlib.pyplot as plt
# import matplotlib.patches as patches
# import random


# def generate_floor_plan():
#     # ---------------------------------------------------------
#     # 1. SETUP
#     # ---------------------------------------------------------
#     model = cp_model.CpModel()

#     # Land Dimensions (e.g., 10m x 10m grid)
#     LAND_WIDTH = 100
#     LAND_HEIGHT = 100
    
#     # Define our rooms with specific requirements (Regulation constraints)
#     # Format: Name, Min Width, Min Height, Min Area
#     rooms_data = [
#         {"name": "Living Room", "min_w": 30, "min_h": 30},
#         {"name": "Bedroom",     "min_w": 25, "min_h": 25},
#         {"name": "Kitchen",     "min_w": 20, "min_h": 20},
#         {"name": "Bathroom",    "min_w": 10, "min_h": 15}
#     ]

#     # Lists to store solver variables
#     all_vars = {} 
#     x_intervals = []
#     y_intervals = []

#     # ---------------------------------------------------------
#     # 2. VARIABLES (Geometric CSP)
#     # ---------------------------------------------------------
#     for room in rooms_data:
#         name = room["name"]
        
#         # 1. Position Variables (X, Y) - Must be inside land
#         x = model.NewIntVar(0, LAND_WIDTH - room["min_w"], f'{name}_x')
#         y = model.NewIntVar(0, LAND_HEIGHT - room["min_h"], f'{name}_y')

#         # 2. Dimension Variables (Width, Height)
#         w = model.NewIntVar(room["min_w"], room["min_w"] + 10, f'{name}_w')
#         h = model.NewIntVar(room["min_h"], room["min_h"] + 10, f'{name}_h')

#         # 3. "End" Variables (Required for OR-Tools Logic)
#         x_end = model.NewIntVar(0, LAND_WIDTH, f'{name}_x_end')
#         y_end = model.NewIntVar(0, LAND_HEIGHT, f'{name}_y_end')

#         # 4. Create "Interval Variables"
#         x_interval = model.NewIntervalVar(x, w, x_end, f'{name}_x_interval')
#         y_interval = model.NewIntervalVar(y, h, y_end, f'{name}_y_interval')

#         x_intervals.append(x_interval)
#         y_intervals.append(y_interval)
        
#         # Store for later drawing
#         all_vars[name] = {'x': x, 'y': y, 'w': w, 'h': h, 'x_end': x_end, 'y_end': y_end}

#     # ---------------------------------------------------------
#     # 3. CONSTRAINTS (The Rules)
#     # ---------------------------------------------------------
    
#     # Rule A: Non-Overlap (The "Physics" Rule)
#     model.AddNoOverlap2D(x_intervals, y_intervals)

#     # Rule B: Adjacency with Complete Channeling
#     # Create boolean variables for each possible adjacency direction
#     touch_right = model.NewBoolVar('kitchen_right_of_living')   # Kitchen on right
#     touch_left = model.NewBoolVar('kitchen_left_of_living')     # Kitchen on left
#     touch_top = model.NewBoolVar('kitchen_above_living')        # Kitchen on top
#     touch_bottom = model.NewBoolVar('kitchen_below_living')     # Kitchen below

#     # Define x_end and y_end relationships first
#     model.Add(all_vars["Living Room"]['x'] + all_vars["Living Room"]['w'] == 
#               all_vars["Living Room"]['x_end'])
#     model.Add(all_vars["Living Room"]['y'] + all_vars["Living Room"]['h'] == 
#               all_vars["Living Room"]['y_end'])
#     model.Add(all_vars["Kitchen"]['x'] + all_vars["Kitchen"]['w'] == 
#               all_vars["Kitchen"]['x_end'])
#     model.Add(all_vars["Kitchen"]['y'] + all_vars["Kitchen"]['h'] == 
#               all_vars["Kitchen"]['y_end'])

#     # ============================================================
#     # CHANNELING CONSTRAINTS (Forward + Backward directions)
#     # ============================================================
    
#     # TOUCH_RIGHT Channeling
#     # Forward: If touch_right = True, Kitchen.x must equal LivingRoom.x_end
#     model.Add(all_vars["Kitchen"]['x'] == all_vars["Living Room"]['x_end']).OnlyEnforceIf(touch_right)
#     # Backward: If touch_right = False, Kitchen.x must NOT equal LivingRoom.x_end
#     model.Add(all_vars["Kitchen"]['x'] != all_vars["Living Room"]['x_end']).OnlyEnforceIf(touch_right.Not())

#     # TOUCH_LEFT Channeling
#     # Forward: If touch_left = True, Kitchen.x_end must equal LivingRoom.x
#     model.Add(all_vars["Kitchen"]['x_end'] == all_vars["Living Room"]['x']).OnlyEnforceIf(touch_left)
#     # Backward: If touch_left = False, Kitchen.x_end must NOT equal LivingRoom.x
#     model.Add(all_vars["Kitchen"]['x_end'] != all_vars["Living Room"]['x']).OnlyEnforceIf(touch_left.Not())

#     # TOUCH_TOP Channeling
#     # Forward: If touch_top = True, Kitchen.y must equal LivingRoom.y_end
#     model.Add(all_vars["Kitchen"]['y'] == all_vars["Living Room"]['y_end']).OnlyEnforceIf(touch_top)
#     # Backward: If touch_top = False, Kitchen.y must NOT equal LivingRoom.y_end
#     model.Add(all_vars["Kitchen"]['y'] != all_vars["Living Room"]['y_end']).OnlyEnforceIf(touch_top.Not())

#     # TOUCH_BOTTOM Channeling
#     # Forward: If touch_bottom = True, Kitchen.y_end must equal LivingRoom.y
#     model.Add(all_vars["Kitchen"]['y_end'] == all_vars["Living Room"]['y']).OnlyEnforceIf(touch_bottom)
#     # Backward: If touch_bottom = False, Kitchen.y_end must NOT equal LivingRoom.y
#     model.Add(all_vars["Kitchen"]['y_end'] != all_vars["Living Room"]['y']).OnlyEnforceIf(touch_bottom.Not())

#     # ============================================================
#     # END OF CHANNELING CONSTRAINTS
#     # ============================================================

#     # At least ONE of these must be true (they touch on at least one side)
#     model.AddBoolOr([touch_right, touch_left, touch_top, touch_bottom])

#     # Add overlap constraints for the perpendicular dimension
#     # If touching horizontally (left/right), must overlap vertically
#     model.Add(all_vars["Kitchen"]['y'] < all_vars["Living Room"]['y_end']).OnlyEnforceIf([touch_right])
#     model.Add(all_vars["Living Room"]['y'] < all_vars["Kitchen"]['y_end']).OnlyEnforceIf([touch_right])
#     model.Add(all_vars["Kitchen"]['y'] < all_vars["Living Room"]['y_end']).OnlyEnforceIf([touch_left])
#     model.Add(all_vars["Living Room"]['y'] < all_vars["Kitchen"]['y_end']).OnlyEnforceIf([touch_left])

#     # If touching vertically (top/bottom), must overlap horizontally
#     model.Add(all_vars["Kitchen"]['x'] < all_vars["Living Room"]['x_end']).OnlyEnforceIf([touch_top])
#     model.Add(all_vars["Living Room"]['x'] < all_vars["Kitchen"]['x_end']).OnlyEnforceIf([touch_top])
#     model.Add(all_vars["Kitchen"]['x'] < all_vars["Living Room"]['x_end']).OnlyEnforceIf([touch_bottom])
#     model.Add(all_vars["Living Room"]['x'] < all_vars["Kitchen"]['x_end']).OnlyEnforceIf([touch_bottom])

#     # ---------------------------------------------------------
#     # 4. SOLVE
#     # ---------------------------------------------------------
#     solver = cp_model.CpSolver()
#     solver.parameters.random_seed = random.randint(0, 1000) 
    
#     status = solver.Solve(model)

#     # ---------------------------------------------------------
#     # 5. PRINT
#     # ---------------------------------------------------------
#     if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
#         print("Solution Found!")
        
#         # Optional: Print which touch direction was chosen
#         print(f"touch_right: {solver.Value(touch_right)}")
#         print(f"touch_left: {solver.Value(touch_left)}")
#         print(f"touch_top: {solver.Value(touch_top)}")
#         print(f"touch_bottom: {solver.Value(touch_bottom)}")
        
#         return {
#             'success': True,
#             'all_vars': all_vars,
#             'solver': solver,
#             'LAND_WIDTH': LAND_WIDTH,
#             'LAND_HEIGHT': LAND_HEIGHT
#         }
#     else:
#         print("No solution found. Constraints might be too tight!")
#         return {
#             'success': False,
#             'all_vars': None,
#             'solver': None,
#             'LAND_WIDTH': LAND_WIDTH,
#             'LAND_HEIGHT': LAND_HEIGHT
#         }


# if __name__ == "__main__":
#     generate_floor_plan()

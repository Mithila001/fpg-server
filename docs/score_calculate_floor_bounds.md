**WARNING : OUTDATED !! IGNORE**

# Implementing New Logic on Optuna for better pre calculations.

## Problem
Currently the current min/max w,h floor bounds are not robust and accurate most of the time. causing infeasible results from the Solver. 

## Objective
You should implement a new Logic to calculate the min/max w,h floor bounds withing the Optunal before each Trial Run.
Here we Modifying the existing logic rather updating it. So NO backward compatibility is Required.

## Plan
- At `app/algorithms/fpg_rooms/fpg_optuna/util` Create a Help Function Called calculate_floor_bounds() and place below logic there.
- From the Algorithm Manager, Take `floor_aspect_ratio`, `max_floor_width`, `max_floor_height` values and provide them to calculate_floor_bounds()
!! Important : calculate_floor_bounds() Should only call withing Optuna app/algorithms/fpg_rooms/fpg_optuna/runner.py. IT should not directly talk with `algorithm_manager_v2.py`
- For each Trail, Optuna Going to setup a Requirement with different w,h values for rooms, and room types. So Per each Trial, after this setup, we call this calculate_floor_bounds() function and provide the Optuna build requirements.
- Withing calculate_floor_bounds() We calculated the total min area required for the given Room template. Here we Add Living Room min value from  `app/core/fpg_rooms/config_fpg.py` ,LIVING_ROOM_MIN_WIDTH,LIVING_ROOM_MIN_HEIGHT. This living Room values will added even the template does not exist the room type 'livingRoom'.
Next, If the Room Template have one or more hallways, for each hallway, get HALLWAY_GENERATOR_MIN_HEIGHT and HALLWAY_GENERATOR_MIN_WIDTH from `config_fpg.py` and calculate the min area that need for hallways.
- After getting the total min area required for the room template, Check if that total min area is Less than or equal to `max_floor_width`*`max_floor_height` area. If not Skip it. Else, Continue
- Now find how much area additionally available by doing (`max_floor_width` * `max_floor_height`) - (total min area). And if the results value is more than 900 square units, `additional_min_area = 900`, if result value is less that 900, then 
Put that 900 value to Config File.
`additional_min_area = what ever that result value is`  Now the total min are should be total min area + additional_min_area
- Now We got valid total min area. Now Calculate the min floor width and min floor height that satisfy total min area. Also this floor min h,w should be follow `floor_aspect_ratio` as min aspect ratio and also withing max_floor_width and max_floor_height bounds. If not, Skip that trial.
- Now we have feasible total min width and height that we can send to the Solver. Return those value to Runner to use in the trial

# New Updates for the Plane
- Instead of the Skipping the Trials during this process, It would be better if the Optuna received a penalty or something like that.
- Ive Notice Runner current implement hard aspect ratios, IT should be changed with above new logic.


Now when i run the generation, It always give the infeasible.
Example Debug logs:
```
START: run_fpg_pipeline_api() ------

 DATA DEBUG ::
<Initial> Floor Width = 180, Floor Height = 200, Room Template = name='Standard 2BHK Layout' data=[{'id': 'bedroom1', 'type': 'bedroom'}, {'id': 'bedroom2', 'type': 'bedroom'}, {'id': 'bathroom1', 'type': 'bathroom'}, {'id': 'kitchen1', 'type': 'kitchen'}] 

 _build_requirements()


 ########## Bypass Data = TRUE ########## 



 DATA DEBUG :
 After Build Requirements = FpgRequirements(rooms=[RoomData(name='bedroom1', type='bedroom', min_w=30, min_h=30, max_w=45, max_h=45), RoomData(name='bedroom2', type='bedroom', min_w=30, min_h=30, max_w=45, max_h=45), RoomData(name='bathroom1', type='bathroom', min_w=15, min_h=25, max_w=20, max_h=32), RoomData(name='kitchen1', type='kitchen', min_w=27, min_h=30, max_w=40, max_h=50)], config=ConfigData(min_coverage=0.5, max_aspect_ratio=16.0, min_aspect_ratio=0.0, floor_plan_width=180, floor_plan_height=200, hallway_count=1, envelope_enabled=True, envelope_min_gap=5, envelope_max_gap=20, envelope_exclude_types=[], envelope_apply_sides=['left', 'right', 'top', 'bottom'], score_geometry_tolerance=1e-06, inward_pocket_max_length=20.0, constraint_hard_basic_geometry=True, constraint_hard_hallway_rules=True, constraint_hard_room_shared_walls=True, constraint_hard_room_adjacency=True, constraint_hard_minimum_area_coverage=True, constraint_hard_room_size_hierarchy=True, constraint_hard_living_room_location=True, constraint_hard_envelope_staircase=True, constraint_soft_seed_layout_hints=True, constraint_soft_room_adjacency_preference=True, constraint_soft_compact_layout_center_proximity=True, constraint_soft_bathroom_location_preference=True, constraint_soft_layout_dead_space_penalty=True, constraint_soft_seed_facade_depth_penalty=True, constraint_soft_seed_facade_alignment_penalty=True, constraint_soft_recessed_facade_penalty=True), relation_constraints=[RoomRelationsConstraint(room_type='bedroom', related_room=['livingRoom'], constraint_level='hard_OR', last_updated='2026-03-25', id=None), RoomRelationsConstraint(room_type='kitchen', related_room=['livingRoom'], constraint_level='hard_AND', last_updated='2026-03-25', id=None), RoomRelationsConstraint(room_type='bathroom', related_room=['hallway'], constraint_level='hard_OR', last_updated='2026-03-25', id=None)])

 _validate_and_compute_floor_bounds()

 DATA DEBUG :
 Validate and Compute Floor Bounds = {'status': 'OK', 'message': 'Floor dimensions validated successfully', 'min_floor_width': 54, 'min_floor_height': 54, 'max_floor_width': 180, 'max_floor_height': 200, 'floor_aspect_ratio': 0.9} 

 DATA DEBUG : Floor dimension bounds object = {'min_floor_width': 54, 'min_floor_height': 54, 'max_floor_width': 180, 'max_floor_height': 200} 

 _select_solver_result()

 _run_optuna_entry() 

========== [DEBUG: calculate_floor_bounds START] ==========
Max Floor: 180x200 (Area: 36000.0)

[DEBUG] Starting _room_min_area calculation...
   - Room: bedroom1 (bedroom), Area: 754.0
   - Room: bedroom2 (bedroom), Area: 864.0
   - Room: bathroom1 (bathroom), Area: 408.0
   - Room: kitchen1 (kitchen), Area: 704.0
   - Living Room (Default), Area: 900.0
   - Hallways (count=1), Total Area: 100.0
[DEBUG] Total Min Area Calculated: 3730.0
Required Area (with buffer): 3730.0 (Buffer: 0.0)
Target Aspect Ratio: 0.9

[DEBUG] Calculating _room_min_extents...
   - Checking bedroom1: max_w=37, max_h=49 -> Current bounds: 37x49
   - Checking bedroom2: max_w=37, max_h=43 -> Current bounds: 37x49
   - Checking bathroom1: max_w=17, max_h=32 -> Current bounds: 37x49
   - Checking kitchen1: max_w=45, max_h=48 -> Current bounds: 45x49
[DEBUG] Final Min Extents Required: 45x49
[DEBUG] Starting iteration for candidate height from 49 to 200...
   - Trying height 49: calculated candidate_width=77
[DEBUG] FOUND valid bounds: 77x49 at height iteration 49
========== [DEBUG: calculate_floor_bounds END (SUCCESS)] ==========


DEV Track 1 


Floor Bounds: FloorBoundsResult(feasible=True, reason='', min_floor_width=77, min_floor_height=49, max_floor_width=180, max_floor_height=200, total_min_area=3730.0, additional_min_area=0.0, required_floor_area=3730.0)


DEV Track 2 


 _run_single_fpg_solve

NOT solved

Results = FpgEvaluationResult(solved=False, solution=[], score_report=None, status='MODEL_INVALID', message='Solver did not return FEASIBLE/OPTIMAL')
est_run_by_trial = {0: FpgEvaluationResult(solved=False, solution=[], score_report=None, status='MODEL_INVALID', message='Solver did not return FEASIBLE/OPTIMAL')}

========== [DEBUG: calculate_floor_bounds START] ==========
Max Floor: 180x200 (Area: 36000.0)

[DEBUG] Starting _room_min_area calculation...
   - Room: bedroom1 (bedroom), Area: 675.0
   - Room: bedroom2 (bedroom), Area: 868.0
   - Room: bathroom1 (bathroom), Area: 336.0
   - Room: kitchen1 (kitchen), Area: 726.0
   - Living Room (Default), Area: 900.0
   - Hallways (count=3), Total Area: 300.0
[DEBUG] Total Min Area Calculated: 3805.0
Required Area (with buffer): 3805.0 (Buffer: 0.0)
Target Aspect Ratio: 0.9

[DEBUG] Calculating _room_min_extents...
   - Checking bedroom1: max_w=46, max_h=48 -> Current bounds: 46x48
   - Checking bedroom2: max_w=55, max_h=55 -> Current bounds: 55x55
   - Checking bathroom1: max_w=18, max_h=35 -> Current bounds: 55x55
   - Checking kitchen1: max_w=39, max_h=41 -> Current bounds: 55x55
[DEBUG] Final Min Extents Required: 55x55
[DEBUG] Starting iteration for candidate height from 55 to 200...
   - Trying height 55: calculated candidate_width=70
[DEBUG] FOUND valid bounds: 70x55 at height iteration 55
========== [DEBUG: calculate_floor_bounds END (SUCCESS)] ==========


DEV Track 1 


Floor Bounds: FloorBoundsResult(feasible=True, reason='', min_floor_width=70, min_floor_height=55, max_floor_width=180, max_floor_height=200, total_min_area=3805.0, additional_min_area=0.0, required_floor_area=3805.0)


DEV Track 2 


 _run_single_fpg_solve

NOT solved

Results = FpgEvaluationResult(solved=False, solution=[], score_report=None, status='MODEL_INVALID', message='Solver did not return FEASIBLE/OPTIMAL')
est_run_by_trial = {0: FpgEvaluationResult(solved=False, solution=[], score_report=None, status='MODEL_INVALID', message='Solver did not return FEASIBLE/OPTIMAL'), 1: FpgEvaluationResult(solved=False, solution=[], score_report=None, status='MODEL_INVALID', message='Solver did not return FEASIBLE/OPTIMAL')}
```

I dont know exactly what is the issues, but i got some my own finding about the issues. 
One of critical issues i found is that you pick the max value of the room type for the calculation. Witch is wrong. for this calculation, what we need are:
- Total Min Area that required for the floor plan (Mean Min area of Each room in room template + living Room min area + hallway min areas if exist only + additional min area) 
- Total Max Area That can floor plan boundary can take
Here we basically checking " Can we fit all required rooms withing the floor plan boundary " logic.

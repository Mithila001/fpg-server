# Implementing New Logic on Optuna for better pre calculations.

## Problem
Currently the current min/max w,h floor bounds are not robust and accurate most of the time. causing infeasible results from the Solver. 

## Objective
You should implement a new Logic to calculate the min/max w,h floor bounds withing the Optunal before each Trial Run.

## Plan
- At `app/algorithms/fpg_rooms/fpg_score/utils` Create a Help Function Called calculate_floor_bounds() and place below logic there.
- From the Algorithm Manager, Take `floor_aspect_ratio`, `max_floor_width`, `max_floor_height` values and provide them to calculate_floor_bounds()
!! Important : calculate_floor_bounds() Should only call withing Optuna app/algorithms/fpg_rooms/fpg_optuna/runner.py. IT should not directly talk with `algorithm_manager_v2.py`
- For each Trail, Optuna Going to setup a Requirement with different w,h values for rooms, and room types. So Per each Trial, after this setup, we call this calculate_floor_bounds() function and provide the Optuna build requirements.
- Withing calculate_floor_bounds() We calculated the total min area required for the given Room template. Here we Add Living Room min value from  `app/core/fpg_rooms/config_fpg.py` ,LIVING_ROOM_MIN_WIDTH,LIVING_ROOM_MIN_HEIGHT. This living Room values will added even the template does not exist the room type 'livingRoom'.
Next, If the Room Template have one or more hallways, for each hallway, get HALLWAY_GENERATOR_MIN_HEIGHT and HALLWAY_GENERATOR_MIN_WIDTH from `config_fpg.py` and calculate the min area that need for hallways.
- After getting the total min area required for the room template, Check if that total min area is Less than or equal to `max_floor_width`*`max_floor_height` area. If not Skip it. Else, Continue
- Now find how much area additionally available by doing (`max_floor_width` * `max_floor_height`) - (total min area). And if the results value is more than 900 square units, `additional_min_area = 900`, if result value is less that 900, then `additional_min_area = what ever that result value is`  Now the total min are should be total min area + additional_min_area
- Now We got valid total min area. Now Calculate the min floor width and min floor height that satisfy total min area. Also this floor min h,w should be follow `floor_aspect_ratio` as min aspect ratio and also withing max_floor_width and max_floor_height bounds. If not, Skip that trial.
- Now we have feasible total min width and height that we can send to the Solver. Return those value to Runner to use in the trial

# New Updates for the Plane
- Instead of the Skipping the Trials during this process, It would be better if the Optuna received a penalty or something like that.
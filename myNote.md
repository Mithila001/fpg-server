# Current state
Right now, I got a functional working flow plan generator project. 

# What my concerns
There are few improvements, clarification and clean up that need to be done for the project, Since the project now being develop for few months, some of the content is not irrelevant and some concept are changed. But the code and logic that related to that old concept still being used ( witch could be headache for long term development) 

Below is the specific point of my concerns 
- Some configure file value might be not being used (orphaned) and some old configure value implementation could violate current project rules (Just an speculation) 
- The given floor width, height and room width, heights, aspect ratios implementation logic could be duplicated or outdated or wrong. 
- During the development of this project with AI, There are placed in the project where if the value is not found, AI place a default value, witch should not happened and should throw and error instead. 

# Scope
- In this moment, we only focus on app/services/algorithm_manager_v2.py file and Optuna implementation and some util file changes only.
- We will not focus  the floor plan generator, score, optuna it self. Rather, we will focus on the data flow before these algorithm being triggered. 

# Tasks
Below, I will explain the flow of the project should go and your task is to modify existing algorithm_manager_v2 to align with it. (ignore backward compatibility)

Before we do anything, From Router section or in algorithm_manager_v2, we need to rounded up the data to integer number, given from api request.This happen AFTER the cm to unit conversion happened. When rounding up, only should round up to lower value. example is 5.5 = 5, 5.3 = 5, 4.9 = 4

1. When the data is received to algorithm_manager_v2 for run_fpg_pipeline_api, We move the _load_server_side_data() and prune_room_relations_constraints_by_template() to run withing _build_requirements() function. 

So that mean First, run_fpg_pipeline_api will do pre validations, then call _build_requirements() function.
This _build_requirements will be withing try catch block, so if any exception error happened, this block will capture it

2. Withing _build_requirements() Do this.
- Update the _build_requirements() parameters for this new logic. 
- try _load_server_side_data and if failed, throw error
- then do prune_room_relations_constraints_by_template

3. Update/replace current room and floor plan normalization and processing
I will explain a flow of how the data process should happen, and you need to remove any existing function related to this and replace those with this new implementations.

Take room_template, floor_width, floor_height, size_constraints

3.1 For room_template, go through each room and assign each room its max w,h and min w,h using `size_constraints` data. If any data is not found in size_constraints, throw an error. No Defaults values. 

3.2 Currently, _run_optuna_entry calls the compute_floor_plan_dimension_bounds() function. we should change that process to do those feature within algorithm manager

Now, withing algorithm manager: 
- Look at floor_width, floor_height. These max possible w and h that flow plan can go. First Create a Configure variable at configure file called `MIN_FLOOR_WIDTH` = 50 and `MIN_FLOOR_HEIGHT` = 50, at the code, check if the given floor width and height is less than for this values. if true, throw an error message saying "Floor dimension are too small"
- Now we checked if the given floor plan is larger that min room sizes. Now we have Floor Width Range (max,min) and Floor Height Range (max,min). Next step is to identify min area required area to place all the room requirements given to us. So for each rooms, get min w,h and get the total min area required for the floor plan. Then for total min required area, add additional 1250 square units (So its not tight space for CP-SAT Solver) . Now check if the total min required area is <= to Max Floor width and height. If true, Then Ok, IF not, Return an Error message. 
- Now know Max w,h and Min possible w,h. Now we should return those value ( max_floor_width, max_floor_height, min_floor_width, min_floor_height range ) to optuna So optuna can change height and width withing those ranges during each trial. Here I'm looking for a footprint that can range from a square up to a 16:9 rectangle. So Optuna can only pick width and height pair that withing those aspect ratio ranges. Optuna should make sure it choosing values are withing those mentioned aspect ratio ranges.
- IF any error happen during the process or empty, null values happened, Throw an error instead of assigning default value that i did not specifically mentioned.




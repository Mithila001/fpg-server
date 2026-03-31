Below is my New Solver idea. I already created `app/algorithms/fpg_finalize` to place this algorithm, Follow same folder and file structure similar to `app/algorithms/fpg_rooms` and `app/algorithms/fpg_opening`


# Idea 
The idea here is to implement an another solver (similar concept to `app/algorithms/fpg_rooms` and `app/algorithms/fpg_opening` by using CP-SAT solver) for optimize/finalize the floor plan. This will run after the `run_quick_post_process` function called in the `app/services/algorithm_manager_v2.py`. Why? Cause the `run_quick_post_process` returns some data that we need for the post process.

Currently, even though i know what should be done to finalize the floor plan. But main issues is HOW it tell to program to do it efficiently and without over complicating. 
So I will give my ideas and concept that I thought, these ideas can be wrong or wright, so don't entirely depend on them and provide you ideas, solutions as well.

# What Will FPGF Receive From The Parent
- This FPGF will receive `quick_post_process_result` from `run_quick_post_process()` function. 
This `quick_post_process_result` have `wall_union` witch is a all room merged single wall segment setup. And also it will contain `room_walls` witch is identical shape to `wall_union` but all the rooms coordinates are stored separately. 
- Also can receive `requirements: FpgRequirements` as well, to have room relations rules and other. 


# Symbolic Labeling
I will give some label for specific concepts so it will be easier me to type. 

FPGF - app/algorithms/fpg_finalize project setup
FPGR - app/algorithms/fpg_rooms project setup
FPGO - app/algorithms/fpg_opening project setup
AM - app/services/algorithm_manager_v2.py code file and the managing concept itself.
DEV - test/dev/finalize-solver area that dedicated for this project dev test
TAPI - test/api/general_api_test.http that will use for quickly test this.
SFLW- Stepped Facade looking walls

# Issues with Generate Plan from `run_quick_post_process`
- There are Dead Space(Air Gaps) withing the arranged rooms in floor plan.
- Unrealistic/Unattractive level of Stepped Facade looking walls at Floor Plan Facade
- Walls that are misaligned withing the floor plan between rooms with small values so it even cannot get as a stylish look.
- Containing unrealistic `recessed wall` shapes on facade walls.


# Requirements  
Here I will write down the requirements I want, There might be some I missed as well.

A: Try To Remove Dead Space as much as possible.
B: Have only few or zero Stepped Facade looking walls.
C: Align internal misaligned walls to make walls practical.
D: Fill up unrealistic `recessed wall` shapes on facade walls


# My ideas and concepts
Now I will describes my ideas for each requirements, Keep in mind these ideas are pure concept that made by me purely by thinking and without research or gathering facts. So you can use this to get an idea about why in my head, but the final solution does not have to be my idea in the sake of `I said it`. 

## Overall Project Idea
Here overall for FPGF, since we working with existing floor plan, we not going *Rearrange* the rooms, we only going to adjust walls. So Here, to reduce the `search space` and to make this solver faster, we should limit the adjustment areas of each points (Reducing the wiggle room), But should not be too much or too little. 

## General Purpose concepts
These are the concept that might or might not be useful to achieve our Requirements easily and robustly.
- Store Facade Wall Segments Coordinates.
- Label Facade walls belongs sides (Front, Back, Left, Right)
- Storing Inner Vertical Walls, Inner Horizontal Walls, Inner Vertical Outer Walls, Inner Horizontal Outer Walls. (Might be better to just separate all wall segments and give list of labels)

## General Rules.
- Adjustments should not exceed given Max Width and Max Height of floor plan
- Should not change the aspect ratios of the room in unrealistic way.

**IMPORTANT**: This FPGF should follow all the importance constraints rules from FPGR so that those rules will not break at FPGF adjustment. Example: Keeping Min two rooms wall overlapping destine, Min width and height of Each Room types, Aspect Ratios like stuff. We dont need to follow all the Rules from FPGR, Just only one that have possibility of violating at FPGF. 
Here its important that we should not import constrains from FPGR and instated we should code here separately. Since both FPGF and FPGR is going to use same `requirement` data, we will have some consistency 

## A: Remove Dead Space,
- Here, If you know a good robust way to find out `Dead Space` withing the floor plan with plain python code, then do it. IF not We can use Shapely for this. We can use `wall_union` and `room_walls` to some boolean stuff.
- So When come to filling up these holes, I can think of two scenarios. Scenario A : Removing a Wall segment so the hole can be part of a other room type. Scenario B : Moving One or Few walls (To their perpendicular axis i think) so the hole will fill up. *In this scenario, I think the Requirements C solution will also help or conflict this.
- When Come to `Removing a wall segment so another room can take the space` concept, we should not just let any dead rooms to join with other rooms, IF the dead room is more that 5 by 5 units, then only they can join, else, stick to wall moving method. 

## B: Stepped Facade looking walls (SFLW)
Here, a SFLW have mainly 3 walls related to it. 2 walls in one direction and other mid wall is to perpendicular direction to setup this SFLW, for that perpendicular direction wall, I will call it `Center Pointer Wall`
Practically, a house can have SFLW, But the current problem is having too much SFLW or unrealistic/ugly SFLW shapes.

- First we need to make sure there will be no Too Larger (more that 20 units) and Too small (less that 5 units) length `Center Pointer Walls`
- Then we need to make sure there are not too much SFLW by implementing this rule. 
    - Front Side will have 0-2 SFLS (Means two `Center Pointer Walls`)
    - Left or Right Side will have a 0 - 1 SFLS (Both of side combined only should have a one SFLS)
    - Back Side will have a 0-1 SFLS

Also I realize there is a possibility that this Concept have a possibility of overlapping or conflating with `Requirement D`. So Keep in mind about that.

## C: Align internal misaligned walls
This is to make the wall in multiple rooms that share same axis have misaligned (not in straight line)
This does not mean every room segment have to be align with every possible closest rooms walls. Example: If there are two Y axis wall (Vertical wall) and the two walls x axis difference is more that 10 units, then alignment might be unnecessary, but if its less that 10 units, then alignment is needed. This can be done to Facade walls as well, but need to keep in mind about not conflicting it with Requirement B and D.

## D: Fill up unrealistic `recessed wall` 
In a recessed wall, typically there are 5 walls involved, Two walls from sided that belongs before and after recessed walls. 2 walls that point perpendicular to other walls (The one direct to inside of the house) And the wall that placed deeper to floor plan (The wall that we need to move outer side direction)

Here I think the only way to fill up this is to move this deep wall to outer direction. Here we don have to make it move out to align with rest of the walls, We can move out it till the recessed wall is not in unrealistic deep like less that 10 unit deep. (This does not mean to avoid making the recessed wall move outside to align with other walls, its also valid)


# Final Info
Now you might starting to notice these concepts are bit similar to FPGR, yes, the constrains are similar, but placing more requirements in there will be too heavy for FPGR and will not provide a fadable results. But here at FPGF, since we already working with a floor plan that generated, now the solver only have a smaller `search space` to look at.
Overall, this FPGF will not be a `do or die` section. Instead simply this setup will take the post processed floor plan, try to make it better quickly and send it. It will not stop the main pipeline just because it cannot find a solution. And when FPGF return the fixed or unfixed floor plan to main pipeline, that floor plan will send to the scoring system and based on the score, the rest of the program will handle rest.

**IMPORTANT**: This FPGF must be a isolated project with single pubic exposing file (a file like `generator.py`) only config import. FPGF should not import any files from other algorithms like FPGR. But can get inspiration and layout structure from FPGR. Currently all Algorithms are isolated like this (Example: FPGR, FPGO) and this new FPGF should follow this as well. (So it easer to debug and maintain a complex project)


# Implementation
Only Add Code withing the `app/algorithms/fpg_finalize` 
Also Create a `app/algorithms/fpg_finalize/dev` folder and create a file called fpgf_debugger.py and here create a function and place it at the end of the FPGF process where this debugger will take before and after floor plan and plot it side by side in a plotter (using matplotlib) and save the image at `app/algorithms/fpg_finalize/dev/output/` folder. This fpgf_debugger.py should have minimum footprint at main FPGF algorithm cause this dev function is temporary and will be delete in future.
- And place this at `app/services/algorithm_manager_v2.py`


scipy

Look at my entire project and tell me if i use scipy (already installed) there, how much better features i can get , or can i improve my existing logic significantly, or is there any significant good new if i use scipy for my project. like able to do something way better that currently with little overheard or less complexity

Here we cannot use SAT solver scoring, the whole goal is to run ton of optuna trial go get best base layout with height score and then use that layout as hint for optuna. (Two Stage Run)

So we definitely need a scoring setup to score when Optuna place hint rooms in floor plan.

So this is my idea for the scoring. Lets assume Optuna place some coordinates in floor plan in a trial. These points are practically rooms hint locations (So i will call them rooms even though they are single points). So there are the potential thing we can score:

- We can use FpgRequirements.relation_constraints and draw lines between related rooms. And if more line getting crossed withing plan, then low score


# Optuna V2
This new version optuna is a experimental implementation against `app/algorithms/fpg_rooms/fpg_optuna` (v1) implementation to check this v2 wil do better performance than current version (v1). Here overall the flow is mostly similar to v1. The main difference with replacing current graphing logic with new logic. others are mostly same. (new v2)

In V1, the graphic implementation with node area + physics did not have good usability to the project (Just my personal opinion/feeling). So in V2, im going to implement bit of new concept. 

## What Will be not changed (mostly)
- The parameters optuna function received from Algorithm Manager
- The Dual State Looping Process where First stage Optuna Run And Second Stage Solver run (V1 Properly implemented this). The dual stage loop will still happen,Optuna will do sampling the solver hint will be still given, difference is now optuna using different scoring logic

# Optuna Sampling Logic
- 

## Relation Implementation between Rooms


# New Score System for Optuna 

# Background of the Project 
This scoring setup will get room location hints (not actual room sized) points (single x,y coordinate per room) from Optuna Trials. Goal is to score it, and return the score to Optuna. This process loop will happen lot of times.
Of Optuna received a good scoring, Optuna will send that to solver as hints for room placements 

Once successfully implement this, we should swap this scoring with current active scoring that optuna use (that graph + physics graph )

# Pre Scoring Setup
Should take requirements : FpgRequirements type as param. This way we can access lot of data like `relation_constraints: list[Any]` and `config: ConfigData` if needed

We using Cartesian coordinate system

New scoring setup will be place at `app/algorithms/fpg_optuna_score`. This is not and should not related to `app/algorithms/fpg_rooms/fpg_graph/score`

## Plan Directions

- In the floor plan, Front -> y- , Back -> y+ , Left -> -x , Right -> +x

## Floor Plan Zones

To analyze the floor plan, we overlay a 3x3 coordinate grid across the boundary. This divides the space into 9 distinct "zones" or "cells," mapped using an (x,y) coordinate system.

We treat the bottom-left corner as the origin (1, 1).

- The first digit (x): Represents the Column (Left to Right).
- The second digit (y): Represents the Row (Bottom to Top).

Row Index,Left Column,Center Column,Right Column
Row 3 (Top),"(1, 3)","(2, 3)","(3, 3)"
Row 2 (Middle),"(1, 2)","(2, 2)","(3, 2)"
Row 1 (Bottom),"(1, 1)","(2, 1)","(3, 1)"

- Defining Zone Ranges (Area Selection)
  When describing a range of zones, we use the syntax (x1, y1) - (x2, y2). This creates a rectangular selection including all cells within those bounds.

Example Ranges
Selection,Type,Total Cells
"(1, 1) - (1, 3)",Full Left Column,3
"(1, 1) - (3, 1)",Full Bottom Row,3
"(2, 2) - (2, 2)",Single Center Cell,1
"(1, 1) - (3, 3)",Entire Floor Plan,9

## Scoring Factors

### Room Zoning Score

Here, we focus on if specific rooms are withing proper locations. We can use each room point coordinates here.

- Check if the veranda is withing 1,1 - 3,1 Zones
- Check if the garage is in 1,1 or 3,1 Zones
- Check if the kitchen is not withing 1,1 - 3,1 AND in 2,2 zones
- Check if the hallway is not withing 1,1 - 3,1
- Check if Living Room withing 1,1 - 3,2 -> Give a Score
- Check if If All bathrooms are not in 1,1 - 3,1 AND 2,2 -> Give a score

### Room Outer Clearance Evaluations (Hard Score)

Some room required have a outer wall in order to expose with land. Here we take the target room point, and if that room desired direction is clear, then score

To evaluate spatial clearance for a room located at (x, y), define a bounding box based on the required "Should Clear Direction". Below is Clearance Zone Breakdown
- Back (y+): Extends from x−10 to x+10 and up to y+20.
- Front (y−): Extends from x−10 to x+10 and down to y−20.
- Left (x−): Extends from x−20 to x and between y−10 and y+10.
- Right (x+): Extends from x to x+20 and between y−10 and y+10.

Do this for:

- Check if veranda room type "Front" side is clear.
- Check if the garage room type "Front" side is clear.
- Check if a kitchen "back" or "left" or "right" side is clear OR check if a hallway "back" side is clear


### Room Relation Integrity Score
- Now we got Optuna sampled room points. 
(Use Already installed NetworkX for this)

Hardcode this to project file
```json
[
  {"rooms": ["kitchen", "hallway"], "cost": 1},
  {"rooms": ["kitchen", "diningRoom"], "cost": 0.5},
  {"rooms": ["livingRoom", "kitchen"], "cost": 1},
  {"rooms": ["livingRoom", "hallway"], "cost": 1},
  {"rooms": ["livingRoom", "veranda"], "cost": 0.5},
  {"rooms": ["livingRoom", "bedroom"], "cost": 2},
  {"rooms": ["bedroom", "hallway"], "cost": 0.5},
  {"rooms": ["bedroom", "attachedBathroom"], "cost": 0.5},
]
```
First need to connect each node with other nodes based on relation and put the cost on the edge line
(if there are multiple room type exists, Ex: 2 rooms type bedroom -> connect both bedrooms to livingRoom)
Spacial Case: when connecting ["bedroom", "attachedBathroom"], connect attachedBathroom with closest bedroom (So only single connection connected to attachedBathroom like in real world where attached bathroom is only connected to a single bedroom)


Now, Run these path calculations:
```json
[
  {"start": "veranda", "end": "livingRoom"},
  {"start": "livingRoom", "end": "bedroom"},
  {"start": "livingRoom", "end": "kitchen"},
  {"start": "livingRoom", "end": "diningRoom"},
  {"start": "livingRoom", "end": "bathroom"},
  {"start": "bedroom", "end": "bathroom"},
  {"start": "kitchen", "end": "diningRoom"},
  {"start": "bedroom", "end": "attachedBathroom"}
]
```
(if there are multiple room type exists, Ex: 2 rooms type bedroom -> run livingRoom to bedroom 1 and run livingRoom to bedroom2 separately)

When Calculating cost for travel, consider the connect edge length(distance) as well, If the distance is x and the cost is 1.5, then total const = x + (x*1.5) 


If there any missing or any edge case happened, instead of just silently giving a default or fallback values, Print a Error/Warning log with `Critical_Graph_Scoring` prefix tag. 



TO visualize how you draw the graph and placed cost edge. Plot that image at `test/outputs/optuna_score/graph` with time stamp image name.
And plot all the best paths calculated per each paths and plot them side by side plots (2 rows and many columns as you want) and save at `test/outputs/optuna_score/pathing`with time stamp.

you can use neworkx plotting feature. You can use `app/algorithms/fpg_optuna_score/dev` if you want to store plotter codes files


## Scoring
Score should distributer like this:
- floor_plan_zones : out of 30
- outer_clearance : out of 20
- room_relations : out of 40


For now, you can determine how scoring should happen internally. 
Score will be given out of 90 total value 

When you implement this, Make sure to add a centralized scoring value modification section at `app/algorithms/fpg_optuna_score/optuna_score_manager.py` so we can quickly adjust how scoring value being added for specific scoring sections.
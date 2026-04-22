# Optuna Behavior Update

Optuna should able to place all node locations coordinates per each trial instead of random seed. Now No room will be randomly placed. All the room locations will decided by the Optuna


# Graph Scoring
When Scoring Most of the time, we can use circle centroid for location identification.

Replace existing Scoring mechanism with this new scoring.
Remove Existing `Front Bonus` evaluation

Put existing Blocked Penalty To hard constrain
Put existing Score evaluation part to Hard Constraint.

## Pre Scoring Setup
### 3x3 Grid Zoning System

To analyze the floor plan, we overlay a 3x3 coordinate grid across the boundary. This divides the space into 9 distinct "zones" or "cells," mapped using an (x,y) coordinate system.

We treat the bottom-left corner as the origin (1, 1).
- The first digit (x): Represents the Column (Left to Right).
- The second digit (y): Represents the Row (Bottom to Top).

Row Index,Left Column,Center Column,Right Column
Row 3 (Top),"(1, 3)","(2, 3)","(3, 3)"
Row 2 (Middle),"(1, 2)","(2, 2)","(3, 2)"
Row 1 (Bottom),"(1, 1)","(2, 1)","(3, 1)"

* Defining Zone Ranges (Area Selection)
When describing a range of zones, we use the syntax (x1, y1) - (x2, y2). This creates a rectangular selection including all cells within those bounds.

Example Ranges 
Selection,Type,Total Cells
"(1, 1) - (1, 3)",Full Left Column,3
"(1, 1) - (3, 1)",Full Bottom Row,3
"(2, 2) - (2, 2)",Single Center Cell,1
"(1, 1) - (3, 3)",Entire Floor Plan,9

### New project scoring file setup
For this new scoring system, we use this file system
app/algorithms/fpg_rooms/fpg_graph/score as room
/score
    /hard_score
        h_room_location.py
        h_outer_clearance.py
    /soft_score
    score_manager.py # the one call all scoring and do the score and return values


# hard and soft score 

## Hard score
There are bool flag scoring. Each evaluation will done and based on success and failures, it will give results out of total hard scoring. (example 4 out of 7) And this score need to be normalize to value 40.

## Soft Scores
These are range scoring. Each evaluation will have range scoring or fixed score value. All score must be normalize to value 50

So now total score is 90.

Here change the Optuna evaluation where if the total Score is less that 80, then its a failed graph result

# Scoring Rules

## Room Location Evaluation (Hard Score)
Here, we focus on if specific rooms are withing proper locations. We can use each room circle center coordinates here.
- Check if the veranda is withing 1,1 - 3,1 Zones
- Check if the garage is in 1,1 or 3,1 Zones
- Check if the kitchen is not withing 1,1 - 3,1 AND in 2,2 zones
- Check if the hallway is not withing 1,1 - 3,1

## Room Outer Clearance Evaluations (Hard Score)
Some room required have a outer wall in order to expose with land. Here we take entire room circle size in to consideration. And We Check if the desired circle desired direction (Front, Back, left, right) is clear from view (Means, hypothetically, if i push the garage room circles to front direction, there should be no other room circles that collide with it. mean front path is clear.)

- Check if veranda room type "Front" side is clear.
- Check if the garage room type "Front" side is clear.
- Check if a kitchen "back" or "left" or "right" side is clear OR check if a hallway "back" side is clear

## Room Location Evaluation (Soft Score)
- If Living Room withing 1,1 - 3,2 -> Give a Score
- If All bathrooms are not in 1,1 - 3,1 AND 2,2 -> Give a score
 
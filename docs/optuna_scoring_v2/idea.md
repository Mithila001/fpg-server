scipy

Look at my entire project and tell me if i use scipy (already installed) there, how much better features i can get , or can i improve my existing logic significantly, or is there any significant good new if i use scipy for my project. like able to do something way better that currently with little overheard or less complexity

Here we cannot use SAT solver scoring, the whole goal is to run ton of optuna trial go get best base layout with height score and then use that layout as hint for optuna. (Two Stage Run)

So we definitely need a scoring setup to score when Optuna place hint rooms in floor plan.

So this is my idea for the scoring. Lets assume Optuna place some coordinates in floor plan in a trial. These points are practically rooms hint locations (So i will call them rooms even though they are single points). So there are the potential thing we can score:

- We can use FpgRequirements.relation_constraints and draw lines between related rooms. And if more line getting crossed withing plan, thent low score

# Pre Scoring Setup

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

### External Room Score

Here, we focus on if specific rooms are withing proper locations. We can use each room point coordinates here.

- Check if the veranda is withing 1,1 - 3,1 Zones
- Check if the garage is in 1,1 or 3,1 Zones
- Check if the kitchen is not withing 1,1 - 3,1 AND in 2,2 zones
- Check if the hallway is not withing 1,1 - 3,1
- Check if Living Room withing 1,1 - 3,2 -> Give a Score
- Check if If All bathrooms are not in 1,1 - 3,1 AND 2,2 -> Give a score

### Room Outer Clearance Evaluations (Hard Score)

Some room required have a outer wall in order to expose with land. Here we take the target room point, and if that room desired direction is clear, then score

When come to finding out the direction, do this. If a room need its back side to be clear, get that room point(`x,y`) and check if there any points at y+ direction that withing point A -> x = `x`-10 , `y` and point B -> x = `x`+10, `y`+20 rectangle area and if there a other points, low marks

Do this for:

- Check if veranda room type "Front" side is clear.
- Check if the garage room type "Front" side is clear.
- Check if a kitchen "back" or "left" or "right" side is clear OR check if a hallway "back" side is clear

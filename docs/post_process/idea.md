The Project will use produce floor plans (simply bunch of rooms arranged according to bunch of constrains) and each plan will go through a Scoring process and only good scored floor plan will chosen.

The goal here is to implement a code logic to fix small mistake that the CP-SAT Solver provided floor plan have so that floor plan could have a change of getting higher score.

Hardest part is implement a robust logic to handle almost all case of the floor plan that receiving. Currently as an external library, I am planning to use Shapely for this since we already using shapely and just default python code for now.

The Code have to keep track of these

- All the room dimentions and locations
- Outer Wall
- Directions of the floor plan (Front, Back, Left, Right)

Current goals are to find gaps (Both internal air gaps and inward gap at th edge of the floor plan boundary) and fill them with correct room type or move the existing rooms.
Easy part is identifying the the issues in the plan, but the hard part is to implement a logic to code to let it decide with solution is the most suitable for the fix.
Here we not going to try to make every floor plan we received perfect, Cause the scoring process can filter out if bad floor plan if it got messed up here.

I have in mind to use Scipy.spatial module for this.( I dont know how it will be useful for my project)

Example Data of floor plan =

```
[{'name': 'bedroom1', 'type': 'bedroom', 'x': 66, 'y': 12, 'w': 34, 'h': 45, 'x_end': 100, 'y_end': 57, 'area': 1530}, {'name': 'bedroom2', 'type': 'bedroom', 'x': 68, 'y': 67, 'w': 45, 'h': 30, 'x_end': 113, 'y_end': 97, 'area': 1350}, {'name': 'bathroom1', 'type': 'bathroom', 'x': 0, 'y': 39, 'w': 20, 'h': 28, 'x_end': 20, 'y_end': 67, 'area': 560}, {'name': 'kitchen1', 'type': 'kitchen', 'x': 113, 'y': 57, 'w': 27, 'h': 35, 'x_end': 140, 'y_end': 92, 'area': 945}, {'name': 'attachedBathroom1', 'type': 'attachedBathroom', 'x': 48, 'y': 67, 'w': 20, 'h': 25, 'x_end': 68, 'y_end': 92, 'area': 500}, {'name': 'veranda1', 'type': 'veranda', 'x': 1, 'y': 0, 'w': 29, 'h': 39, 'x_end': 30, 'y_end': 39, 'area': 1131}, {'name': 'garage1', 'type': 'garage', 'x': 100, 'y': 0, 'w': 40, 'h': 57, 'x_end': 140, 'y_end': 57, 'area': 2280}, {'name': 'diningRoom1', 'type': 'diningRoom', 'x': 0, 'y': 67, 'w': 48, 'h': 30, 'x_end': 48, 'y_end': 97, 'area': 1440}, {'name': 'livingRoom1', 'type': 'livingRoom', 'x': 30, 'y': 0, 'w': 36, 'h': 57, 'x_end': 66, 'y_end': 57, 'area': 2052}, {'name': 'hallway1', 'type': 'hallway', 'x': 20, 'y': 57, 'w': 93, 'h': 10, 'x_end': 113, 'y_end': 67, 'area': 930}, {'name': 'verandaOutdoorSpace_for_veranda1', 'type': 'verandaOutdoorSpace', 'x': 0, 'y': 0, 'w': 1, 'h': 39, 'x_end': 1, 'y_end': 39, 'area': 39}]
```

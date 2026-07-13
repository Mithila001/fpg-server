# Stop Process Command

Add new API endpoint to Stop already running Solver processors. This is a hard stop.

# Hallway Improvements.

- Check if hallway width have a range or its
- Hallway have to be more that just single rectangle.

# Floor Plan Boundary Preprocessing

- Floor Plan boundary should be more practical. First get the max area needed for the floor plan. Then add another 50% of area value of it. Then Calculate the width and height we can get while keeping the aspect ratio of 10:16
- Also Let Optuna Change the Orientation of the floor plan

# Graph Generation

Give Veranda - Garage Higher Score
Check if the Bathroom-Hallway Relation weight is tight

# Why even new Inward pocket score seems give fail score, but the project make it final floor plan


# When Opening Generation
- Avoid overlapping Doors and Windows
- Door placement logic change - Highly prioritize Living Room - Veranda Door Connection Rather Hallway Connection
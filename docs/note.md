# Optuna Fix
In the current implementation, there is an issues. Even though optuna decided hallways counter for graphs, the room requirement that send to solver does not have that hallway amount created. Only hint have correct hallway count. So i need to change the code so before providing room list to solver, based on solver chose hallway count, modify the room list hallways as well to align for that.

# Graph New Soft Scoring
- Score if the dining room is not in 2,1 OR 1,3 - 3,3 Area
- Score if the all the bedrooms and attached bathrooms are closer to each other, score, if far apart, lower score

# Generation Time limit Check issues
I believe the Time Out Feature at app/algorithms/fpg_rooms/fpg_optuna/runner.py is not working. It tested with TRIAL_OPTIMIZATION_TIMEOUT_SECONDS = 3 and that did not stop the process after 3 second and continue till all the trial count ended or a feasible solution is received.
Need to fix it.

# Stop Process Command
Add new API endpoint to Stop already running Solver processors. This is a hard stop.
We going to do major modification for this project. Due to complexity of the implementation, this implementation will happen in few 
phases.
Overall the this modification goal is to implement optun + graph base floor plan arrangement and use the good graph for the solver as hint.
Some part of the project will be not work till full phase is done.

# Phase 1 (Status - Ongoing)
This phase focus on implementing ground work for the new implementation. Main goal in this phase is to modify existing optua and solver initial generation. 

- Now, the optuna will not do trial per solver logic. The optuna will not the one call for the Solver and provide data.
- Now, the Solver should have the ability to received hint coordinated points (single coordinate point hint per room) for initial generation as well (These are not hard seeds, only soft initial placement hints). These hint should be Optinal for the solver.
- Still the solver will received the min,max h,w as usual.  Now additionally, solver will received hint for initial generation. Hint will apply one for first initial generation.


Change the `app/services/algorithm_manager_v2.py` file so now it does not call the _run_single_fpg_solve per each trial. We still going to use optuna in the project, but not to call _run_single_fpg_solve per each trial. So at `app/services/algorithm_manager_v2.py`, you can remove any optuna related stuff and just keep the `_run_single_fpg_solve` function for now. 

Optuna section (`app/algorithms/fpg_rooms/fpg_optuna`) will be use for different trial run. But thats not phase 1 task.

Overall goal is to clean up the `app/services/algorithm_manager_v2.py` for future implementations and modify Solver to take hints. 
And I will expect the project run_fpg_pipeline_api function to not work with this implementations
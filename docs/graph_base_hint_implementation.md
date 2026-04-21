We going to do major modification for this project. Due to complexity of the implementation, this implementation will happen in few 
phases.
Overall the this modification goal is to implement optun + graph base floor plan arrangement and use the good graph for the solver as hint.
Some part of the project will be not work till full phase is done.

# Phase 1 (Status - Done)
This phase focus on implementing ground work for the new implementation. Main goal in this phase is to modify existing optua and solver initial generation. 

- Now, the optuna will not do trial per solver logic. The optuna will not the one call for the Solver and provide data.
- Now, the Solver should have the ability to received hint coordinated points (single coordinate point hint per room) for initial generation as well (These are not hard seeds, only soft initial placement hints). These hint should be Optinal for the solver.
- Still the solver will received the min,max h,w as usual.  Now additionally, solver will received hint for initial generation. Hint will apply one for first initial generation.


Change the `app/services/algorithm_manager_v2.py` file so now it does not call the _run_single_fpg_solve per each trial. We still going to use optuna in the project, but not to call _run_single_fpg_solve per each trial. So at `app/services/algorithm_manager_v2.py`, you can remove any optuna related stuff and just keep the `_run_single_fpg_solve` function for now. 

Optuna section (`app/algorithms/fpg_rooms/fpg_optuna`) will be use for different trial run. But thats not phase 1 task.

Overall goal is to clean up the `app/services/algorithm_manager_v2.py` for future implementations and modify Solver to take hints. 
And I will expect the project run_fpg_pipeline_api function to not work with this implementations


# Phase 2 (Stats - Done)
In this phase, we focus on Graph Implementation.

All the code related to graph (util, types and more) should store at `app/algorithms/fpg_rooms/fpg_graph` use folder /physics for graph physics, and you can create new folder withing `app/algorithms/fpg_rooms/fpg_graph` if needed or change /physics folder name if needed.

Graph main task is to take values like nodes, connecting, weight as such from anyone who call it main public function, do the physics simulation and stuff and return the graph result.

Now I will give you my whole note So you can get clear idea about why/how the node graph will be going to use. But that does not mean you have to implement below task Some of task are future phase. Just use it to get an knowledge. Focus on phase 3 only.



# Phase 3 (Stats - Not Started)
In this phase, the main focus is replacing existing optuna logic with brand new optuna logic.
This new Optuna focus on mutating a graph that represent floor plan relations.

Now the Optun Behave like this At `app/services/algorithm_manager_v2.py` a new function called `run_fpg()` will get triggered. When it triggered, `run_fpg()` will provide typical room data and requires that already exist in algorithm_manager_v2

And First , We need to construct ranges of that Optuna can play around. I don;t have a clear idea about it, but i will write down what i can think of.
- We can use room relations for node connect, Hard AND relation, Hard OR relations and Normal optional relations. 
- Hallway Implementation. Here optuna can decide hallways count. 
- I think there are some i mention at below `My Note` as well

Now there is an important flow we have to implement. This is bit complex compare to current flow.

The flow is like this

1. API Start
2. run_fpg()
3. Run Optuna Trial
Here the trial process is different now. Lets say the max trial count = 100 and timeout time is 60second(currently using this value already)
Here, this is how the flow work.
- Optuan Run Trial and get Graph Scores. If Optuna Received a Good Score, It call a function called `run_solver()` (this function can either sit on algorithm manager or suitable other place). But importantly, optuna is not done yet, its waiting. 
This `run_solver()` will take a value called `FPG_SOLVER_RUN_COUNT` = 2 and run the Solver with hints and requirements data for `FPG_SOLVER_RUN_COUNT` amount of time till get a good `fpg_score` value. IF not got an score or infeasible results withing those solver call rounds, it will return false message, 
Of return false, Optuna continue the trial where it stop before, till get a another good `graph_score` and do the iteration till get a feasible results, time out, or trial count ends.

Here, as you can see, there are two main iterations work as nested loops.
- Outer Iteration -> Optuna Build a Graph -> Run Physics -> Score Graph -> Call Inner Iteration if Graph Score is height > Loop back
- Inner Iteration -> Get Optuna Provided Data + Graph, build the setup so Solver can take it without issues and Send to Solver -> Get FPG Score -> Evaluate and if the score is low and infeasible, Loop based on `FPG_SOLVER_RUN_COUNT` -> Return results

As you can see, now the Optuna does not directly work with Solver, there is a specific function that call solver, check fpg results.
Now the Optuna focus on graph generation. 

Here let graph score to cap to 90, and let other 10 score value to get from `run_solver()` So Optuna have a ida if the given graph to `run_solver()` gave a good results or not 


My Note (Keep in mind some of below note content could be outdated)
```
To optimize the layout of the node group, we utilize Force-Directed Graph mechanics to prevent nodes from either clumping together or expanding too far apart. In this system, every connection between nodes functions like a physical spring where the "weight" of the connection determines its stiffness. Connections with high weight create high-stiffness springs, pulling those specific nodes closer together to represent a strong relationship. Conversely, low-weight connections result in low-stiffness springs, allowing the nodes to drift further apart and move more freely within the layout.

Each node group is contained within a fixed boundary defined by the floor plan’s width and height, which typically maintains an aspect ratio between 1:1 and 1:2. All individual nodes must fit entirely inside this area without crossing its edges, though they are not required to fill the entire space. While the nodes can be arranged in various ways, specific types like the veranda or garage are generally positioned toward the front of the boundary to reflect the house's entrance.

## Circle size calculation
Each node is represent as a circle. And each circle area(size) is difference based on the room type. the circle size will calculate like this:
for each room, get it's min,max w,h value (for hallway, use fpg_config hallway values) and get midpoint width and midpoint height. Now find the circle size that can fit withing that rectangle, that thats the rectangle size representing that room.

## Node Connection weights
The connection wight = 1 is normal connection, anything between 0-1 is low connection and 1-2 is high connection (close connections)

### Node Relation Implementations logic
Use `app/algorithms/fpg_rooms/constraints/hard/room_adjacency_hard.py`, `app/algorithms/fpg_rooms/constraints/hard/hard_dining_room_relation.py` and `app/algorithms/fpg_rooms/constraints/hard/hallway_constraints.py` to get an idea about the how the relation implementation between room work. Look at `test/db-mock/room_relations_constraints.json` to see actual room relation data. 

# The optuna Simulation
The optuna will give coordinate values for each node. And once those are placed in the boundary. The physics engine will run. The physics loop until the nodes stop moving significantly (And safety limit value so the physics loop will not run non stop in case of error/bug). This physics will follow Force-Directed Graph mechanics, pulling nodes based on their spring stiffness, and prevent overlaps of node and other logics to achieve Force-Directed Graph mechanics.
Add hallways based on optuna choice, use `DEFAULT_HALLWAY_COUNT` value as starting point. 


# Scoring
For this, lets do a basic scoring for now. Simply check if the room adjacent is satisfied by calculating the room connection stretch and connection weight also if the adjacent rooms are not block/separated by other room. Some rooms have more that one option to satisfy the connections (Example: diningRoom).
- Also check if the veranda and garage are at front most of the house. Give 50 scores for this. IF the total score is more that 40, then thats a usable layout. And provide that to optuna.
```

Overall implement this phase. I think with this phase, we will have an end to end implementations.

Currently the Optuna Node Placement is not satisfying my needs. One of the main reason is after observing the plotter images of "optuna placed graph layout " and "after physics simulation run graph layout " for lot of graph trials, I notice that optuna node placement kind of not influencing much on the process. The physics simulation is the one heavily influencing there. So that mean optuna kind of less useful.
But I don wanna use optuna for this.

So after some thinking, this is my idea.

- We keep all node in same size till physics runs
- We keep the current optuna limited search space method with high `OPTUNA_SEARCH_SPACE_GRID_SCALE`. In that way all optuna picked node location have high impact on final physicians run Rather letting optuna place node in low `OPTUNA_SEARCH_SPACE_GRID_SCALE` where node can be place closer to each other in small area of the floor plan.
- Let optuna place point without considering the node size
- After Optuna Placed the node. Let the Graph Physicians to run. But this time. the first let the physicians run with identical node size. This way node can first focus on relations and there location without being blocked by other node.
- Then inflate the node so all nodes take proper sized

I Hope this approach will alow to make Optuna More useful for the project

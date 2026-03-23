I provided you a markdown file containing project info. Read it first and get an idea about the situation.

Now, After some attempts, Its look like i don't have greater flexibly to adjust the Solver behavior based on my requirements. The main problem is not about solver being strict, its about some features like removing adding variable and other features are not available or not reliable.
So I am thinking about creating a another intelligent feature (Solver Controller) that could adjust the parameters of the solver before solver initiate. Current I have to manually add/remove/edit variables in code to get the desired requirements. I am planning to replace this with a `Solver Controller`
Currently, the program steps are,
Provide DB Data -> Initialized the Solver -> Run the Solver -> Get and Process results -> Output
But with new implementation,
Provide DB Data -> Solver Controller Adjust parameters -> Solver Controller Trigger `Solver` -> Run the Solver -> Get and Process results -> Validation Score ->  Loop again to [Solver Controller Adjust parameters] -> So on till get desired score.

Here we can ignore the `Validation Score` for now, and only focus on `Solver Controller`

OK, that the idea, but my main issues, I don't know what to do or how to do it, i don't know what kind of option i have, what are best for this, what are most suitable for this and so on. I'm blind here with a imaginary concept.

So i need your help with it. I need a brain storm, a guide, a recommendation that and work with my existing project. 

Keep in mind this is not about replacing existing solver, the solver keep doing the floor plan arranging part. the new feature will do what the solver cannot do, "Changing variables and constrain before solver initializing. Solver will keep be the smart guy, but the Solver Controller will the fine tune data that going to provided to the solver.

I'm using python programming language for the project 


# Current Updated info base on small researches 
- Thinking about using Optuna for `Solver Controller`
- And a custom scoring system first using basic python and if feasible, using Shapely, NetworkX as improvements.

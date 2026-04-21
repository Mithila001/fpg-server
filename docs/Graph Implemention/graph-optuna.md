Current algorithm_manager_v2 + Optuna + Solver flow is incorrect. below is a rough explanation of the flow i actually need.

As you know right now, there are two Scoring System, FPG Score at `app/algorithms/fpg_rooms/fpg_score` and graph score at `app/algorithms/fpg_rooms/fpg_graph/score` 

I want the optuna to run multiple trials till get a best graph score and then use that graph is as hint layout for solver and let solver run few time with that hints if solver did not return a good score, then optuna continue that previous run and so on.

Below is the rough flow example of the process

1 API Start
2 All the pre configuration will done by algorithm_manager_v2
3 Start Floor Plan Generation (Assume the Max Timeout = 60s and Max Trial Count = 100)
4 Optuna Start The Process
4.1 Optuna Setup a Graph and Run the Trials till get a high score results (Graph score will be out of 90)
    4.1.1 Trial: 1,  Score Result: Low, Status: Failed
    4.1.2 Trial: 2,  Score Result: Low, Status: Failed
    4.1.3 Trial: 3,  Score Result: Low, Status: Failed
    4.1.4 Trial: 4,  Score Result: High, Status: Passed 
4.2 NowCall the Solver manager related function, who get that graph score > process it so Solver can use it > Run the Solver FPG_SOLVER_RUN_COUNT amount of time till get passing score. The either after getting results or loop end, then only return.
- If the results score is give passed, then Process should stop and return that floor plan as usable floor plan.
- If the result score is low and failed, Return give solver scored fpg Score
4.3 Optuna received a score (with mean the solver failed) and normalize it to 10/100 amount. That way this fpg score can be add to graph score (90 + 10). In scenario where Graph score is failed (low), here automatically the fpg score will be 0 out of 10 (Since these results are not even worth to go to solver)
4.4 Now Optuna know there are still time and trial count left to use. So Optuna continues from where it left
    4.4.1 Trial: 1,  Score Result: Low, Status: Failed
    4.4.2 Trial: 2,  Score Result: Low, Status: Failed
    4.4.3 Trial: 3,  Score Result: High, Status: Passed 
4.5 Solver Run Couple time with this new results, got low score, return that to Optuna and optuna still have time and trial count left so
    4.5.1 Trial: 1,  Score Result: Low, Status: Failed
    4.5.2 Trial: 2,  Score Result: Low, Status: Failed
    4.5.3 Trial: 3,  Score Result: Low, Status: Failed
    4.5.4 Trial: 4,  Score Result: High, Status: Passed
4.6 Here optuna send this result to Solver, Solver run first time -> Got failed, Run Again, got passing fpg score, whole process stopped and return the valid floor plan.



# Reasoning
- The Reason I 90/100 for Graph Score and 10/100 for normalized fpg Score is So the Optuna knows something happened in Solver based on that 10 value changes.
- The Reason Iam Not letting Optuna run Solver for each trial is to improve performance, A Solver can take 2-5 seconds for a solution. And the optuna need minimum 100 trial to be actually useful. And running 5*100 seconds for a floor plan is not good. But the Graph Generation is fast, So we can run 100 trial for graph generation to get good result and use that for Solver. Even in Solver, We run the same graph results few times repeatedly just so make sure that graph is actually usable or not.
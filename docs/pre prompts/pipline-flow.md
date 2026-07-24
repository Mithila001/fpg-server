I need the pipeline flow to be like this

I will use these shorten name for the explanations
- Candidate Search - Hint
- Candidate Score - Hint Score
- Floor Plan Solver - FPG
- Flor Plan Score - FPG Score



There should be config values for (these name can be change to appropriate namings)
eligible_hint_score = 80
trial_count = 100
time_out = 60s

usable_fpg_score = 80
presentable_fpg_score = 90

fpg_run_count = 2


When the pipeline starts:
Run the whole pipeline till it completed time_out or presentable_fpg_score is gotten from a floor plan. If not, if the usable_fpg_score passed floor plan exist, then send it. If also that not exist as well. then no floor plan found message.

During the pipeline run.
Run the Hint for trial_count
And when a hint got a Hint Score >= eligible_hint_score; then temporary stop the hint generation, then send those hint to FGP and do the process. here run the FPG Score, and FPG Score >= presentable_fpg_score , we got one and send it to client and stop the pipeline. if not, lets say we got a FPG Score tht >= usable_fpg_score and FPG Score <= presentable_fpg_score. Then keep the floor plan and run FPG again with same hint point if the fpg_run_count is not 0 still. If the FPG score is < usable_fpg_score, then go back to Hint section and continue the trial from where it stopped before. Run the whole process till either trial count ends or time out triggered
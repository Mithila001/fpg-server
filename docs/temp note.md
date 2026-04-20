Carefully look at both validate_and_compute_floor_bounds() function and calculate_floor_bounds() function. Both are have similar logics. But calculate_floor_bounds() more complex that other.

Now the plan is to modify validate_and_compute_floor_bounds() is purely act as API validator instead or providing floor values `bounds_result` and help with `floor_dimension_bounds` creation. In this new implementation, the `algorithm_manager_v2.py` will not provide `floor_dimension_bounds` value to optuna. It wil handled by calculate_floor_bounds() function.
Here validate_and_compute_floor_bounds() will be modified to additionally add living room min w,h and single hallway min h,w to its calculation. The `MIN_FLOOR_AREA_BUFFER` at config_fpg.py will be also added.
validate_and_compute_floor_bounds() will simply focus on validation of API and return error if invalid. Will not contribute for any other work.

At calculate_floor_bounds() function will not get max_floor_width: int, max_floor_height: int, now. Instead use `requirements.config.floor_plan_width` and `requirements.config.floor_plan_height` value as max floor width and max floor height.
`floor_aspect_ratio` also should not get from param and should calculated internally with  max floor width and max floor height that just got.
This calculate_floor_bounds() will call per each Optuna trial to provide (before Optuna building requirement data per trial). If This calculate_floor_bounds() give invalid, Simply return 0 score to optuna


Keep in mind, this is rough plan, I might mistaken some, if you found something confusing, simply ask questions from me



-------------------------


I dont like this logic, Lets Change it. So my plan is this.
- We already have `max_floor_area`, `max_floor_width`,`max_floor_height`, `total_min_area` 
So what I now want is min_width = x and min_hight = y, what is the the x,y value that satisfy `x*y == total_min_area`
Here there should also follow another two rules
    1. The Aspect Ratio should be between 1:1 and 1:2
    2. The Starting Width should be 50 unit (if the `max_floor_width` is lower than that, use `max_floor_width` as starting width)
If the calculation evolved float numbers, we can do calculation in float numbers and at the end before sending the data, we can round them up to integers 


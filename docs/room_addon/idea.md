Currently in my CP-SAT solver floor plan generation, it only generate 4 side rectangles for all rooms. To make this more flexible and letting some room to have more that just simple rectangle shape, here, we providing extender rooms for some of room types to use. This extender rooms will always attached to its parent(target) room. And in the post process, these extender rooms will be merge in to its parent room, treat both as one single room.

We Should use profiling similar to `fpgr_p_refine_1.py` concept in this situations. We will call this new profile `fpgr_p_refine_extender` And here, this profile will have the fpgr_p_refine_1 logic, but also `fpgr_p_refine_extender` will have additional logic as well. (Mean fpgr_p_refine_extender will have fpgr_p_refine_1 characteristics as well)

In this `fpgr_p_refine_extender` section, the new extender rooms will be added to empty space existing in the seeded room layout. This will the extender room will work as a "filler" instead of a new room that need to worry about.

Constraint related to this extender room types will be added at `app/algorithms/fpg_rooms/constraints/extenders` folder

Each extender room will have a active status. If active = false, the room width and height will be 0. IF the active == true, then the extender room min with = 10 and min height = 10, and max w,h = 30 

What extender room going to add, who is its parent and how many extender room info should be hard coded withing `fpgr_p_refine_extender` profile file.

Each extender room must have a parent/target room. extender room will be attached to parent room once

For Now, these are the constrain that need to follow
- extender room one side wall should be attached to parent room fully overlapping that wall.


For now add a single living room extender room to floor plan. (We will add more in future if this work correctly)

After Creating the file, call this at app/services/algorithm_manager_v2.py


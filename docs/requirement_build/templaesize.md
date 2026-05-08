I got an issue with Room requirement Size implementation.

Currently My API payload is like this

http://localhost:8000/algorithms/format/v2
{
"floor_width": 1500,
"floor_height": 1500,
"aspect_ratio": "1.6:1",
"room_template": {
"name": "Standard 2BHK Layout",
"data": [
{ "id": "bedroom1", "type": "bedroom", "size": "regular" },
{ "id": "bedroom2", "type": "bedroom", "size": "regular" },
{ "id": "bathroom1", "type": "bathroom", "size": "regular" },
{ "id": "kitchen1", "type": "kitchen", "size": "regular" },
{ "id": "attachedBathroom1", "type": "attachedBathroom", "size": "regular" },
{ "id": "veranda1", "type": "veranda", "size": "regular" },
{ "id": "garage1", "type": "garage", "size": "regular" },
{ "id": "diningRoom1", "type": "diningRoom", "size": "regular" }
]
},
"should_optuna_run": true,
"optuna_trial_count": 500
}

This works and give floor plan results.

But the problem occurring when i change "size" to small or large (these are the other time available to use, you can look in to the project `test\db-mock\room_size_constraints.json` to get an idea about how the structure work.). The problem is when i pick `small` or `large` size type, the floor all Solver generating initialization become quickly infeasible.(this is not happening in `regular` size mode) I think some constraint is messing with it. So the obvious one i can think of is `CONSTRAINT_HARD_ROOM_SIZE_HIERARCHY` constraint, So i disable it, but still the issue is there.

But I think i found the issue (Not sure it the actual issue though)
I found a problem where living room is always in 'regular' mode and cannot change to 'large' or 'small' dynamically. So assuming this is the issues, I have some ideas that needed to be implement.

In the app\util\algorithm_manager\build_requirements.py, modify existing code to achieve this:

When received `room_template: RoomSetupTemplateBase` Check what are the majority "size" type and pick that one as the room_size_category (So even though we let each room to provide a size, here we generalize it and pick a common one)

So now all rooms are in that room_size_category

Now, when adding livingRoom, pick the room_size_category as it selected size type.

I know we got the hallway as well, but lets ignore it, hallways are not typically get lot more wider when the rest of the room becomes large. Ignore Hallways.

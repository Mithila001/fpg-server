In a Floor Plan layout, A veranda should be at front of the house. And then the living room unusually attach back or one side to it. Even though in floor plan generation, we take the veranda as a another room, to make it realistic, we must make sure that front and usually one side of the veranda should not connect with other rooms. 

Initially I though about creating a dedicated constraint specifically for veranda. But now I am thinking about more general purpose constraint for this. Since the veranda is a open room type (Where 1 or more non wall sides contains) We can name it like open_area_placement so we can use this for other rooms like garage in future.

So if I summaries this
- The target room front facing wall (I think in the algorithm, front mean bottom most section in the floor plan) and other wall that connect to front facing wall (could be from either side of the front facing wall). 
- And other room wall should be available for attach with other room types. (Witch room is going to attach to this room will be decided by apply_hard_room_adjacency_constraints so dont worry about that)

For now, do this: if the given room list have a room type = veranda , then apply this constrain for that room.

Can you add that hard constraint at app/algorithms/fpg_rooms/constraints/hard
and apply it to constraint_control_panel.py
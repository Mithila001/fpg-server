Wow, that sounds great. Let create a plan for it. I will again note down some info and the new constraints as well
*The Content below is written by me based on your explanation and how i understood about it, So there might be some info that wrong, ignore or give less value to the info I am wrong about*

For the Core, create a file name called `fpgr_core,py` 
And For profile 1, `fpgr_p_generate.py`
And For profile 2, `fpgr_p_refine_1.py`

Wiggle Room = 10 units

# Constraints
Here for this Session, Only Focus on implementing Constraint B, ignore rest. We will implement once we successfully able to implement this setup

## A: Remove Dead Space,
- Here, If you know a good robust way to find out `Dead Space` withing the floor plan with plain python code, then do it. IF not We can use Shapely for this. We can use `wall_union` and `room_walls` to some boolean stuff.
- So When come to filling up these holes, I can think of two scenarios. Scenario A : Removing a Wall segment so the hole can be part of a other room type. Scenario B : Moving One or Few walls (To their perpendicular axis i think) so the hole will fill up. *In this scenario, I think the Requirements C solution will also help or conflict this.
- When Come to `Removing a wall segment so another room can take the space` concept, we should not just let any dead rooms to join with other rooms, IF the dead room is more that 5 by 5 units, then only they can join, else, stick to wall moving method. 

## B: Stepped Facade looking walls (SFLW)
Here, a SFLW have mainly 3 walls related to it. 2 walls in one direction and other mid wall is to perpendicular direction to setup this SFLW, for that perpendicular direction wall, I will call it `Center Pointer Wall`
Practically, a house can have SFLW, But the current problem is having too much SFLW or unrealistic/ugly SFLW shapes.

- First we need to make sure there will be no Too Larger (more that 20 units) and Too small (less that 5 units) length `Center Pointer Walls`
- Then we need to make sure there are not too much SFLW by implementing this rule. 
    - Front Side will have 0-2 SFLS (Means two `Center Pointer Walls`)
    - Left or Right Side will have a 0 - 1 SFLS (Both of side combined only should have a one SFLS)
    - Back Side will have a 0-1 SFLS

There is a another rules set:
- If Front Facing Room Count Is less that 1, No SFLW should exist
- If Left or Right facing Room count is less that 2, No SFLW should exist
- If Back Facing Room Count Is less that 1, No SFLW should exist

Also I realize there is a possibility that this Concept have a possibility of overlapping or conflating with `Requirement D`. So Keep in mind about that.

## C: Align internal misaligned walls
This is to make the wall in multiple rooms that share same axis have misaligned (not in straight line)
This does not mean every room segment have to be align with every possible closest rooms walls. Example: If there are two Y axis wall (Vertical wall) and the two walls x axis difference is more that 10 units, then alignment might be unnecessary, but if its less that 10 units, then alignment is needed. This can be done to Facade walls as well, but need to keep in mind about not conflicting it with Requirement B and D.

## D: Fill up unrealistic `recessed wall` 
In a recessed wall, typically there are 5 walls involved, Two walls from sided that belongs before and after recessed walls. 2 walls that point perpendicular to other walls (The one direct to inside of the house) And the wall that placed deeper to floor plan (The wall that we need to move outer side direction)

Here I think the only way to fill up this is to move this deep wall to outer direction. Here we don have to make it move out to align with rest of the walls, We can move out it till the recessed wall is not in unrealistic deep like less that 10 unit deep. (This does not mean to avoid making the recessed wall move outside to align with other walls, its also valid)
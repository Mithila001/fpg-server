I am currently facing an issue where this new 'veranda' and 'garage' room types are not exactly placing like i want to. So in this session, we going to try a concept. Throw me some ideas if you find one .
Since i dont have a clear idea about a successfully constrain setup for this specific rooms, we going to implement all constrain at app/algorithms/fpg_rooms/constraints/hard/open_area_placement.py and organize them later on.

Task:
The current rule, 'Keep veranda/garage front and at least one lateral side open,' is negatively impacting veranda rooms. Currently, the solver identifies available space next to a veranda room and attempts to place another room there. However, because the 'two-face open' rule prevents the rooms from being attached, the solver places them with a gap between the walls instead of allowing them to share a common wall. 
So, I need a solution that satisfy multiple requirement between rooms.
So This is my idea:
### For Veranda
Here, we need to have clear idea about room wall location, witch wall is left, witch wall is right, front and back. In the solver, the front mean the bottom of the coordinates. (So bottom mean house front side. i will use front and back terms here)

- In the veranda room type, Front wall must be the outer most front wall of the floor plan.
- Now for this Front Wall, there are two connected wall segments, The rule here should be is "From these two wall segments, Only one wall segment is allowed to connect with other room types and second wall segment should connect with a room type call 'verandaOutdoorSpace' (I will explain it below).

When come to this 'verandaOutdoorSpace' its a trick to make the veranda placement more realistic by giving it more exposure to outside. How it behavior is, verandaOutdoorSpace is only looking for a wall segment in 'veranda' room type where it can attached to, once it sees it, verandaOutdoorSpace attach one wall of its to veranda allowed wall. verandaOutdoorSpace should make sure to cover entire length of that veranda wall. Now its going to scale perpendicular wall to veranda attache wall and scale itself to 30 units max (can be lower if not possible to move 30 units). Goal here is to not let actaul room type to take place there. verandaOutdoorSpace will take that space and in post processing, we can convert verandaOutdoorSpace to empty space (But dont worry about post process now)


For the Garage, its simple, Must expose front Wall to outside. Other walls can attach with what ever other room types. 





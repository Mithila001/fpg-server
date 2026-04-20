OK, lets keep thinking about this. I still got to get a full idea about this.

There are few questions/tasks i need to figure out.
1. How to store this graph as data in the project and how to tell Optuna to modify it? Like should i give heuristic guide or should let Optuna let to its own changes by its own.
2. After create a proper graph, how to provide that to Solver as hint. Like what should need to worry? i mean what does solver ask when providing hint? If solver only need rought area hint (since the graph more about relation and not actual distance and between rooms) or Do i need to give precision locations or room centers.
3. Using Optuna with 50 trials will be make enough differece compare to just randomizing grap without optuna?
4.How to make sure graph is spread and not strack on top of each other poitns and shrink too closer or expand too wider.
5.Since thee floor plan is box shape, how this graph can adap to more boxier shape rather circle shape. 

And other issues that im not aware of 


Below is my idea of how the graph should behave. (this is just a concept, this could be wrong)

- Each point represent a room center (not absolute center, just some general location)
- I decided we not going to store area value in each node. this graph more focus on relations
- Edges have weights. Based on weighted level, it determined the how closer the bond between those two rooms (Example: dining room - kitchen node will have high weight score cause those two room are typically closer to each other. If one room move, other room will drag with it.). Two rooms that have very low weight are loosely connected. 
- Each Node connected edge have a angle vales. This way node can track there other connected node locations. (and also Optuna can control them). To make this simpler, Only parent node store angle or its children's. 
- Each edge will have same length, we will not use node edge length for the evaluations.
- Every Node does not have to be connected with all each other nodes. only need ones that truly need a connection. But all node must have a direct or indirect connection (So no room will not left alone)
- Whole node graph will not represent a circle shape. And also the anchor, super parent node will not be at the center, it mostly will be at front (bottom side if you draw this graph in a paper and look at it)


Overall, my plane is to place this graph to the flow plan, Since the program will give both floor width and height. we simply fit this graph inside that box by scaling down or up(floor plan boundary) and now each node have a coordinate point at the floor plan, and now we just get those coordinate and give those as rough general room placement area hints. Here its impotent that the graph sit withing the floor plan boundary.






------------------------- 2


In this graph-based spatial model, each node represents an individual room, while each edge defines a specific relationship or transition between them. To ensure a valid configuration, every room must possess at least one direct connection to another, and the entire network must be fully connected. This implies that while every node is not required to share a direct edge with every other node, a continuous traversal path must exist between any two points in the system. For instance, if Room A and Room C are not directly linked, the requirement is still satisfied provided an indirect path exists through an intermediary, such as A→B→C

> Storage 

> passing hints

> Optuna Trials

To optimize the layout of the node group, we utilize Force-Directed Graph mechanics to prevent nodes from either clumping together or expanding too far apart. In this system, every connection between nodes functions like a physical spring where the "weight" of the connection determines its stiffness. Connections with high weight create high-stiffness springs, pulling those specific nodes closer together to represent a strong relationship. Conversely, low-weight connections result in low-stiffness springs, allowing the nodes to drift further apart and move more freely within the layout.

Each node group is contained within a fixed boundary defined by the floor plan’s width and height, which typically maintains an aspect ratio between 1:1 and 1:2. All individual nodes must fit entirely inside this area without crossing its edges, though they are not required to fill the entire space. While the nodes can be arranged in various ways, specific types like the veranda or garage are generally positioned toward the front of the boundary to reflect the house's entrance.

> Circle size calculation
Each node is represent as a circle. And each circle area(size) is difference based on the room type  

# The optuna Simulation
The optuna will give coordinate values for each node. And once those are placed in the boundary. The physics engine will run. The physics loop until the nodes stop moving significantly (And safety limit value so the physics loop will not run non stop in case of error/bug). This physics will follow Force-Directed Graph mechanics, pulling nodes based on their spring stiffness, and prevent overlaps of node and other logics to achieve Force-Directed Graph mechanics.


> Scoring




> Next Phase. 
You can represent a hallway as a string of small circles rather than one big one.
The "Rigid Bone" Rule: Instead of letting the circles move freely, you treat the hallway as a Chain of Circles where the connections are locked to the X or Y axis.

If the hallway is a "string," it has more "surface area" for other rooms to attach to. To keep your system from getting confused, you should treat the Hallway as a "Container" or a "Super-Node."
These inner circles should be placed so they are touching or slightly overlapping. If each circle has a radius r, the distance between their centers should be exactly 2r
Instead of picking one circle (first or last), let the Bedroom node connect to the entire hallway string using a "Floating Edge."
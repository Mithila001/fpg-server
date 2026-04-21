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
> Front End Input changes
Currently the front end send data like in this format

```
POST http://localhost:8000/algorithms/format/v2
Content-Type: application/json

{
	"floor_width": 180,
	"floor_height": 200,
	"room_template": {
		"name": "Standard 2BHK Layout",
		"data": [
			{ "id": "bedroom1", "type": "bedroom" },
			{ "id": "bedroom2", "type": "bedroom" },
			{ "id": "bathroom1", "type": "bathroom" },
			{ "id": "kitchen1", "type": "kitchen" },
			{ "id": "attachedBathroom1", "type": "attachedBathroom" },
			{ "id": "veranda1", "type": "veranda" },
			{ "id": "garage1", "type": "garage" },
			{ "id": "diningRoom1", "type": "diningRoom" }
			
		]
	},
	"should_optuna_run": true,
	"optuna_trial_count": 50
}
```
But now with new update, it will send data like this
POST http://localhost:8000/algorithms/format/v2
Content-Type: application/json

{
	"floor_width": 180,
	"floor_height": 200,
	"room_template": {
		"name": "Standard 2BHK Layout",
		"data": [
			{ "id": "bedroom1", "type": "bedroom", "size_class": "large" },
			{ "id": "bedroom2", "type": "bedroom", "size_class": "medium"  },
			{ "id": "bathroom1", "type": "bathroom" , "size_class": "medium" },
			{ "id": "kitchen1", "type": "kitchen" , "size_class": "medium"  },
			{ "id": "attachedBathroom1", "type": "attachedBathroom" , "size_class": "medium" },
			{ "id": "veranda1", "type": "veranda" , "size_class": "small" },
			{ "id": "garage1", "type": "garage" , "size_class": "medium" },
			{ "id": "diningRoom1", "type": "diningRoom" , "size_class": "medium" }
			
		]
	},
	"should_optuna_run": true,
	"optuna_trial_count": 50
}

At app/util/algorithm_manager/build_requirements.py we need to do major changes to the logics and flow.

Currently the `size_constraints` will give data like this format
```json
[
  {
    "type": "bedroom",
    "min_w": 30,
    "max_w": 45,
    "min_h": 30,
    "max_h": 45,
    "min_area": 900,
    "max_area": 2025,
    "preset_id": "standard_bed"
  },
  {
    "type": "kitchen",
    "min_w": 27,
    "max_w": 40,
    "min_h": 30,
    "max_h": 50,
    "min_area": 810,
    "max_area": 2000,
    "preset_id": "standard_kitchen"
  },
]
```
But with new version, the `size_constraints` will have data like this

```json
[
  {
    "type": "bedroom",
    "base_values":{
        "w" : 30,
        "area" : 1000
    },
    "size_class":{
        "small":{
            "w_add": -3,
            "area_add": -200,
            "max_value_add" : 5,
        },
        "medium":{
            "w_add": 0,
            "area_add": 0,
            "max_value_add" : 5,
        },
        "large":{
            "w_add": 30,
            "area_add": 500,
            "max_value_add" : 10,
        }
    },
    "preset_id": "standard_bedroom"
  },....
]
```

With this new data, now should do calculation to create min_w, min_h, max_w, max_h
Example: IF the given Room size_class == "small" for the bedroom. then the 
- min_w = base_values.w + size_class.<given_size_class>.w_add
- min_h = (base_values.area + size_class.<given_size_class>.area_add ) / min_w
- max_w = min_w + size_class.<given_size_class>.max_value_add
- max_h = min_h + size_class.<given_size_class>.max_value_add


> start 

In this graph-based spatial model, each node represents an individual room, while each edge defines a specific relationship or transition between them. To ensure a valid configuration, every room must possess at least one direct connection to another, and the entire network must be fully connected. This implies that while every node is not required to share a direct edge with every other node, a continuous traversal path must exist between any two points in the system. For instance, if Room A and Room C are not directly linked, the requirement is still satisfied provided an indirect path exists through an intermediary, such as A→B→C

> Storage 



> Optuna Trials

To optimize the layout of the node group, we utilize Force-Directed Graph mechanics to prevent nodes from either clumping together or expanding too far apart. In this system, every connection between nodes functions like a physical spring where the "weight" of the connection determines its stiffness. Connections with high weight create high-stiffness springs, pulling those specific nodes closer together to represent a strong relationship. Conversely, low-weight connections result in low-stiffness springs, allowing the nodes to drift further apart and move more freely within the layout.

Each node group is contained within a fixed boundary defined by the floor plan’s width and height, which typically maintains an aspect ratio between 1:1 and 1:2. All individual nodes must fit entirely inside this area without crossing its edges, though they are not required to fill the entire space. While the nodes can be arranged in various ways, specific types like the veranda or garage are generally positioned toward the front of the boundary to reflect the house's entrance.

## Circle size calculation
Each node is represent as a circle. And each circle area(size) is difference based on the room type. the circle size will calculate like this:
for each room, get it's min,max w,h value (for hallway, use fpg_config hallway values) and get midpoint width and midpoint height. Now find the circle size that can fit withing that rectangle, that thats the rectangle size representing that room.

## Node Connection weights
The connection wight = 1 is normal connection, anything between 0-1 is low connection and 1-2 is high connection (close connections)

### Node Relation Implementations logic
Use `app/algorithms/fpg_rooms/constraints/hard/room_adjacency_hard.py`, `app/algorithms/fpg_rooms/constraints/hard/hard_dining_room_relation.py` and `app/algorithms/fpg_rooms/constraints/hard/hallway_constraints.py` to get an idea about the how the relation implementation between room work. Look at `test/db-mock/room_relations_constraints.json` to see actual room relation data. 

# The optuna Simulation
The optuna will give coordinate values for each node. And once those are placed in the boundary. The physics engine will run. The physics loop until the nodes stop moving significantly (And safety limit value so the physics loop will not run non stop in case of error/bug). This physics will follow Force-Directed Graph mechanics, pulling nodes based on their spring stiffness, and prevent overlaps of node and other logics to achieve Force-Directed Graph mechanics.
Add hallways based on optuna choice, use `DEFAULT_HALLWAY_COUNT` value as starting point. 


# Scoring
For this, lets do a basic scoring for now. Simply check if the room adjacent is satisfied by calculating the room connection stretch and connection weight also if the adjacent rooms are not block/separated by other room. Some rooms have more that one option to satisfy the connections (Example: diningRoom).
- Also check if the veranda and garage are at front most of the house. Give 50 scores for this. IF the total score is more that 40, then thats a usable layout. And provide that to optuna.


> passing hints
After getting a Good Score result, those node coordinates will be pass to the Solver as Hints. 


> Next Phase. 
You can represent a hallway as a string of small circles rather than one big one.
The "Rigid Bone" Rule: Instead of letting the circles move freely, you treat the hallway as a Chain of Circles where the connections are locked to the X or Y axis.

If the hallway is a "string," it has more "surface area" for other rooms to attach to. To keep your system from getting confused, you should treat the Hallway as a "Container" or a "Super-Node."
These inner circles should be placed so they are touching or slightly overlapping. If each circle has a radius r, the distance between their centers should be exactly 2r
Instead of picking one circle (first or last), let the Bedroom node connect to the entire hallway string using a "Floating Edge."



















POST http://localhost:8000/algorithms/format/v2
Content-Type: application/json

{
	"floor_width": 300,
	"floor_height": 300,
	"room_template": {
		"name": "Standard 2BHK Layout",
		"data": [
			{ "id": "bedroom1", "type": "bedroom", "size_class": "medium" },
			{ "id": "bedroom2", "type": "bedroom", "size_class": "medium"  },
			{ "id": "bathroom1", "type": "bathroom" , "size_class": "medium" },
			{ "id": "kitchen1", "type": "kitchen" , "size_class": "medium"  },
			{ "id": "attachedBathroom1", "type": "attachedBathroom" , "size_class": "medium" },
			{ "id": "veranda1", "type": "veranda" , "size_class": "medium" },
			{ "id": "garage1", "type": "garage" , "size_class": "medium" },
			{ "id": "diningRoom1", "type": "diningRoom" , "size_class": "medium" }
			
		]
	},
	"should_optuna_run": true,
	"optuna_trial_count": 10
}



[
  {
    "type": "bedroom",
    "base_values": {
      "w": 36,
      "area": 1400
    },
    "size_class": {
      "small": {
        "w_add": -6,
        "area_add": -450,
        "max_value_add": 5
      },
      "medium": {
        "w_add": 0,
        "area_add": 0,
        "max_value_add": 5
      },
      "large": {
        "w_add": 6,
        "area_add": 500,
        "max_value_add": 10
      }
    },
    "preset_id": "standard_bedroom"
  },
  {
    "type": "kitchen",
    "base_values": {
      "w": 30,
      "area": 1000
    },
    "size_class": {
      "small": {
        "w_add": -6,
        "area_add": -300,
        "max_value_add": 3
      },
      "medium": {
        "w_add": 0,
        "area_add": 0,
        "max_value_add": 5
      },
      "large": {
        "w_add": 6,
        "area_add": 400,
        "max_value_add": 8
      }
    },
    "preset_id": "standard_kitchen"
  },
  {
    "type": "livingRoom",
    "base_values": {
      "w": 39,
      "area": 2000
    },
    "size_class": {
      "small": {
        "w_add": -6,
        "area_add": -600,
        "max_value_add": 5
      },
      "medium": {
        "w_add": 0,
        "area_add": 0,
        "max_value_add": 10
      },
      "large": {
        "w_add": 9,
        "area_add": 1000,
        "max_value_add": 15
      }
    },
    "preset_id": "standard_living"
  },
  {
    "type": "diningRoom",
    "base_values": {
      "w": 36,
      "area": 1450
    },
    "size_class": {
      "small": {
        "w_add": -6,
        "area_add": -450,
        "max_value_add": 4
      },
      "medium": {
        "w_add": 0,
        "area_add": 0,
        "max_value_add": 6
      },
      "large": {
        "w_add": 6,
        "area_add": 650,
        "max_value_add": 10
      }
    },
    "preset_id": "standard_dining"
  },
  {
    "type": "bathroom",
    "base_values": {
      "w": 15,
      "area": 500
    },
    "size_class": {
      "small": {
        "w_add": -3,
        "area_add": -175,
        "max_value_add": 2
      },
      "medium": {
        "w_add": 0,
        "area_add": 0,
        "max_value_add": 3
      },
      "large": {
        "w_add": 3,
        "area_add": 200,
        "max_value_add": 5
      }
    },
    "preset_id": "standard_bathroom"
  },
  {
    "type": "attachedBathroom",
    "base_values": {
      "w": 15,
      "area": 450
    },
    "size_class": {
      "small": {
        "w_add": -3,
        "area_add": -150,
        "max_value_add": 2
      },
      "medium": {
        "w_add": 0,
        "area_add": 0,
        "max_value_add": 3
      },
      "large": {
        "w_add": 5,
        "area_add": 250,
        "max_value_add": 5
      }
    },
    "preset_id": "ensuite_bathroom"
  },
  {
    "type": "garage",
    "base_values": {
      "w": 36,
      "area": 2200
    },
    "size_class": {
      "small": {
        "w_add": -6,
        "area_add": -550,
        "max_value_add": 5
      },
      "medium": {
        "w_add": 0,
        "area_add": 0,
        "max_value_add": 5
      },
      "large": {
        "w_add": 19,
        "area_add": 1000,
        "max_value_add": 10
      }
    },
    "preset_id": "standard_garage"
  },
  {
    "type": "veranda",
    "base_values": {
      "w": 24,
      "area": 1200
    },
    "size_class": {
      "small": {
        "w_add": -6,
        "area_add": -400,
        "max_value_add": 3
      },
      "medium": {
        "w_add": 0,
        "area_add": 0,
        "max_value_add": 20
      },
      "large": {
        "w_add": 12,
        "area_add": 800,
        "max_value_add": 10
      }
    },
    "preset_id": "standard_veranda"
  }
]
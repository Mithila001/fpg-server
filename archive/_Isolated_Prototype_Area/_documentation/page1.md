# FPG Documentation

---

## Basic Rules

### Basic Constraints

Entry Function: `add_basic_constraints`
Param:
Parameter | Info
--- | --- |
model | info|
all_vars | info|
x_intervals | info|
y_intervals | info|

_**Return**: No Return, Existing Model Modifications_

1. Non overlap constraint

```javascript
model.AddNoOverlap2D(x_intervals, y_intervals);
```

2. Room End Vertex x,y values

```javascript
model.Add(vars_dict["x"] + vars_dict["w"] == vars_dict["x_end"]);
....
```

---

### Adjacency Constraints

#### General Purpose Function

**adjacency_constraints.py** file is responsible for this logic. `add_adjacency_constraint` general purpose function will be use to add common adjacency. Other function will be define for custom adjacency requirements.

Private Function: `add_adjacency_constraint`
Param:
Parameter | Info
--- | --- |
model | info|
room1_vars | Target Room|
room2_vars | info|
room1_name | info|
room2_name | info|

This Function contains following rules

At leas one must be true for given two rooms:

- Touch Right
- Touch Lef
- Touch Top
- Touch Bottom

**Note:**

- Currently Checking only if at leas two walls are touch little bit or not. Need rules to let the both Rooms touch enough walls area for entry placements

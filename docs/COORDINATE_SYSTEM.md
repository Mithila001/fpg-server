# Coordinate System & Directional Convention

This document establishes the canonical coordinate system used throughout the floor-plan generation (FPG) solver and constraints. All directional references (front, back, left, right) must conform to these definitions to ensure consistency across hard constraints, soft constraints, and post-processing.

## Screen Perspective (Viewer Looking Down at Floor Plan)

```
                Back (y_max)
                     ↑
                     |
          +----------+----------+
          |                     |
Left      |    FLOOR PLAN       |   Right
(x=0)     |    (View from       |   (x=max)
          |     above)          |
          |                     |
          +----------+----------+
                     |
                     ↓
               Front (y=0)
```

## Coordinate Mapping

| Direction | Screen Position | Coordinate Range | Axis | Notes |
|-----------|-----------------|------------------|------|-------|
| **Front** | Bottom of screen | y → 0 (minimum) | y-axis | House entrance, road-facing side, exterior opening |
| **Back** | Top of screen | y → maximum | y-axis | Interior side, typically backs onto other properties |
| **Left** | Viewer's left | x → 0 (minimum) | x-axis | When looking at floor plan from above |
| **Right** | Viewer's right | x → maximum | x-axis | When looking at floor plan from above |

## Axis Definitions

### X-Axis (Horizontal)
- **Origin (x=0):** Left edge of floor plan
- **Direction:** Increases toward right
- **Range:** `[0, floor_width]`

### Y-Axis (Vertical on Screen / Depth in Floor Plan)
- **Origin (y=0):** Front of floor plan (street-facing, entrance side)
- **Direction:** Increases toward back
- **Range:** `[0, floor_height]`

## Room Variables

Every room has four position/dimension variables:

```
Room Position Variables:
  x        : x-coordinate of left edge (room.x in [0, floor_width - room.min_w])
  y        : y-coordinate of front edge (room.y in [0, floor_height - room.min_h])
  x_end    : x-coordinate of right edge (x_end = x + w)
  y_end    : y-coordinate of back edge (y_end = y + h)
  w        : width (left-right extent)
  h        : height (front-back extent)

Visual on floor plan (view from above):
  (x, y_end)         (x_end, y_end)
       +-----------------+           Back (y_max)
       |                 |
       |     ROOM        |
       |                 |
       +-----------------+
  (x, y)           (x_end, y)
                           Front (y=0)

Walls:
  Front wall: segment from (x, y) to (x_end, y)        — Lower y value
  Back wall:  segment from (x, y_end) to (x_end, y_end) — Higher y value
  Left wall:  segment from (x, y) to (x, y_end)        — Lower x value
  Right wall: segment from (x_end, y) to (x_end, y_end) — Higher x value
```

## Wall Contacts (Touch Constraints)

When two rooms touch (share a wall), the contact is checked via coordinate alignment:

- **Left-side touch:** `room1.x_end == room2.x` (room1's right wall touches room2's left wall)
- **Right-side touch:** `room1.x == room2.x_end` (room1's left wall touches room2's right wall)
- **Front-side touch:** `room1.y == room2.y_end` (room1's front wall touches room2's back wall)
- **Back-side touch:** `room1.y_end == room2.y` (room1's back wall touches room2's front wall)

## Special Rules for Veranda & Garage

### Veranda Placement (Hard Constraint)
- **Front wall location:** `veranda.y == 0` (always on the front boundary of the floor plan)
- **Rationale:** Veranda provides the main entrance; must be street-facing
- **Back wall:** Can attach to any room type (interior connection)
- **Side walls:** Exactly one side (left or right) must attach to `verandaOutdoorSpace`; the other side may attach to other rooms or remain open

### Garage Placement (Hard Constraint)
- **Front wall location:** `garage.y == 0` (street-facing, exterior access required)
- **Rationale:** Garage needs direct external access for vehicles
- **Back wall:** Can attach to other rooms (typically for entry into house)
- **Side walls:** No special attachment rules

### verandaOutdoorSpace (Generated Auxiliary Room)
- **Purpose:** Reserve outdoor space adjacent to veranda for patio/garden visibility
- **Attachment:** One full side wall of `verandaOutdoorSpace` must match one veranda side wall (y and y_end must align)
- **Expansion:** Expands horizontally (x-axis) in opposite direction from veranda attachment:
  - If attached to veranda's left side → expands left (toward x=0)
  - If attached to veranda's right side → expands right (toward x=max)

## Center-Y Anchor Rule (Room Location)

**With veranda present:**
- Veranda serves as the frontage anchor
- Constraint: `veranda.y + veranda.y_end ≤ other_room.y + other_room.y_end` for all other rooms
- Ensures veranda center does not extend further back than any other room's center

**Without veranda (fallback):**
- LivingRoom serves as the anchor
- Constraint: `living_room.y + living_room.y_end ≥ other_room.y + other_room.y_end` for all other rooms
- Legacy behavior: keeps living room as the deepest-placed room toward the back

## Code References

- Hard constraints: `app/algorithms/fpg_rooms/constraints/hard/`
- Soft constraints: `app/algorithms/fpg_rooms/constraints/soft/`
- Room model: `app/algorithms/fpg_rooms/solver_models/room.py`
- Open-area placement: `app/algorithms/fpg_rooms/constraints/hard/open_area_placement.py`
- Room location: `app/algorithms/fpg_rooms/constraints/hard/room_location_hard.py`

# """Open-area placement constraints for veranda and garage frontage.

# Coordinate System Reference (see docs/COORDINATE_SYSTEM.md):
#   - Front = y=0 (bottom of screen, street-facing)
#   - Back  = y=max (top of screen, interior)
#   - Left  = x=0 (viewer's left)
#   - Right = x=max (viewer's right)

# This module enforces veranda and garage placement at the front boundary (y=0)
# and manages verandaOutdoorSpace expansion for patio/garden visibility.
# """

# from __future__ import annotations

# from typing import Dict, List

# from ortools.sat.python import cp_model

# from ...solver_models.room import Room


# def _touch_constraints(
#     model: cp_model.CpModel,
#     room1: Room,
#     room2: Room,
# ) -> Dict[str, cp_model.IntVar]:
#     suffix = f"oa_{room1.name}_{room2.name}"

#     assert room1.x is not None and room1.y is not None
#     assert room1.x_end is not None and room1.y_end is not None
#     assert room2.x is not None and room2.y is not None
#     assert room2.x_end is not None and room2.y_end is not None

#     touch_right = model.NewBoolVar(f"{suffix}_right")  # type: ignore
#     touch_left = model.NewBoolVar(f"{suffix}_left")  # type: ignore
#     touch_top = model.NewBoolVar(f"{suffix}_top")  # type: ignore
#     touch_bottom = model.NewBoolVar(f"{suffix}_bottom")  # type: ignore

#     model.Add(room1.x == room2.x_end).OnlyEnforceIf(touch_right)
#     model.Add(room1.x != room2.x_end).OnlyEnforceIf(touch_right.Not())

#     model.Add(room1.x_end == room2.x).OnlyEnforceIf(touch_left)
#     model.Add(room1.x_end != room2.x).OnlyEnforceIf(touch_left.Not())

#     model.Add(room1.y == room2.y_end).OnlyEnforceIf(touch_top)
#     model.Add(room1.y != room2.y_end).OnlyEnforceIf(touch_top.Not())

#     model.Add(room1.y_end == room2.y).OnlyEnforceIf(touch_bottom)
#     model.Add(room1.y_end != room2.y).OnlyEnforceIf(touch_bottom.Not())

#     return {
#         "right": touch_right,
#         "left": touch_left,
#         "top": touch_top,
#         "bottom": touch_bottom,
#     }


# def _add_non_overlap_constraint(
#     model: cp_model.CpModel,
#     room_a: Room,
#     room_b: Room,
#     name: str,
# ) -> None:
#     assert room_a.x is not None and room_a.y is not None
#     assert room_a.x_end is not None and room_a.y_end is not None
#     assert room_b.x is not None and room_b.y is not None
#     assert room_b.x_end is not None and room_b.y_end is not None

#     a_left = model.NewBoolVar(f"{name}_a_left")  # type: ignore
#     a_right = model.NewBoolVar(f"{name}_a_right")  # type: ignore
#     a_below = model.NewBoolVar(f"{name}_a_below")  # type: ignore
#     a_above = model.NewBoolVar(f"{name}_a_above")  # type: ignore

#     model.Add(room_a.x_end <= room_b.x).OnlyEnforceIf(a_left)

#     model.Add(room_b.x_end <= room_a.x).OnlyEnforceIf(a_right)

#     model.Add(room_a.y_end <= room_b.y).OnlyEnforceIf(a_below)

#     model.Add(room_b.y_end <= room_a.y).OnlyEnforceIf(a_above)

#     model.AddBoolOr([a_left, a_right, a_below, a_above])


# def _create_veranda_outdoor_space(
#     model: cp_model.CpModel,
#     veranda: Room,
#     land_width: int,
#     land_height: int,
# ) -> Room:
#     vos = Room(
#         name=f"verandaOutdoorSpace_for_{veranda.name}",
#         min_w=1,
#         min_h=1,
#         max_w=100,
#         max_h=100,
#         type="verandaOutdoorSpace",
#     )
#     vos.create_variables(model, land_width, land_height)
#     return vos


# def add_open_area_placement_constraints(
#     model: cp_model.CpModel,
#     rooms: List[Room],
# ) -> List[Room]:
#     """Apply hard veranda frontage and generated verandaOutdoorSpace placement rules.

#     Returns list of created verandaOutdoorSpace auxiliary rooms that must be added to
#     the main room list for solution extraction.

#     Hard Rules:
#       1. Veranda front wall is always on y=0 (front/street-facing boundary).
#       2. Veranda back wall can attach to any room type (interior).
#       3. Exactly one veranda side wall (left OR right) must attach to verandaOutdoorSpace.
#       4. verandaOutdoorSpace expands horizontally opposite to attachment side:
#          - Left attachment → expand left (x → 0)
#          - Right attachment → expand right (x → floor_width)
#       5. verandaOutdoorSpace is blocked from overlapping other real rooms.
#       6. Garage front wall also on y=0 (front/street-facing, vehicle access).
#       7. Garage must be positioned at front-left corner (x=0) or front-right corner (x=land_width).
#     """
#     real_rooms = [room for room in rooms if room.type != "verandaOutdoorSpace"]
#     verandas = [room for room in real_rooms if room.type == "veranda"]
#     garages = [room for room in real_rooms if room.type == "garage"]
#     created_auxiliary_rooms: List[Room] = []
    
#     if not verandas and not garages:
#         return created_auxiliary_rooms

#     # Keep bounds finite without relying on solver proto domains.
#     land_width = max(30, sum(max(1, room.max_w) for room in real_rooms))
#     land_height = max(30, sum(max(1, room.max_h) for room in real_rooms))

#     # Constrain all garage rooms to the front (y=0) for street-facing access.
#     for garage in garages:
#         assert garage.x is not None and garage.y is not None
#         assert garage.x_end is not None and garage.y_end is not None
#         # Front wall of garage is always on y=0 (street-facing, vehicle access).
#         # y=0 is the minimum y value, anchoring garage at the front boundary.
#         model.Add(garage.y == 0)
        
#         # Garage must be positioned at front-left corner or front-right corner (not center).
#         # Create two boolean variables: one for each corner option.
#         garage_at_left = model.NewBoolVar(f"{garage.name}_at_left_corner")  # type: ignore
#         garage_at_right = model.NewBoolVar(f"{garage.name}_at_right_corner")  # type: ignore
        
#         # Define what each condition means with bidirectional constraints.
#         # Left: garage.x near 0 (within first 10 units)
#         model.Add(garage.x <= 10).OnlyEnforceIf(garage_at_left)
#         model.Add(garage.x > 10).OnlyEnforceIf(garage_at_left.Not())
        
#         # Right: garage.x_end near land_width (within last 10 units)
#         model.Add(garage.x_end >= land_width - 10).OnlyEnforceIf(garage_at_right)
#         model.Add(garage.x_end < land_width - 10).OnlyEnforceIf(garage_at_right.Not())
        
#         # Force EXACTLY one corner (mutually exclusive: left XOR right)
#         # This means: (left AND NOT right) OR (NOT left AND right)
#         model.AddBoolOr([garage_at_left, garage_at_right])  # At least one
#         model.Add(garage_at_left + garage_at_right == 1)     # Exactly one

#     for veranda in verandas:
#         assert veranda.x is not None and veranda.y is not None
#         assert veranda.x_end is not None and veranda.y_end is not None

#         # Front side of veranda is always on y=0 (street-facing, entrance).
#         # y=0 is the minimum y value, anchoring veranda at the front boundary.
#         model.Add(veranda.y == 0)

#         vos = _create_veranda_outdoor_space(model, veranda, land_width, land_height)

#         # The generated outdoor space reserves area, so normal rooms cannot overlap it.
#         for other in real_rooms:
#             if other.name == veranda.name:
#                 continue
#             _add_non_overlap_constraint(model, vos, other, f"oa_non_overlap_{vos.name}_{other.name}")

#         veranda_vos_touches = _touch_constraints(model, veranda, vos)
#         attach_left_side = veranda_vos_touches["right"]
#         attach_right_side = veranda_vos_touches["left"]

#         # Exactly one side wall adjacent to the front must attach to verandaOutdoorSpace.
#         model.Add(attach_left_side + attach_right_side == 1)

#         # Enforce side-wall attachment only.
#         model.Add(veranda_vos_touches["top"] == 0)
#         model.Add(veranda_vos_touches["bottom"] == 0)

#         assert vos.x is not None and vos.y is not None
#         assert vos.w is not None and vos.h is not None
#         assert vos.x_end is not None and vos.y_end is not None
#         assert veranda.h is not None

#         # Shared wall must span the full veranda side height.
#         model.Add(vos.y == veranda.y)
#         model.Add(vos.y_end == veranda.y_end)
#         model.Add(vos.h == veranda.h)

#         # On left-side attachment, outdoor space fills from x=0 up to veranda's left wall.
#         model.Add(vos.x_end == veranda.x).OnlyEnforceIf(attach_left_side)
#         model.Add(vos.x == 0).OnlyEnforceIf(attach_left_side)

#         # On right-side attachment, outdoor space fills from veranda's right wall to boundary.
#         model.Add(vos.x == veranda.x_end).OnlyEnforceIf(attach_right_side)
#         model.Add(vos.x_end == land_width).OnlyEnforceIf(attach_right_side)
        
#         created_auxiliary_rooms.append(vos)
    
#     return created_auxiliary_rooms

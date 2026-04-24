# fpg_Rooms Constraints

## Hard constraints
- Basic
- Envelope staircase
- Floor Area Coverage 
- Hallway Constraints
- Room Adjacency Hard
- Room Location Hard
- Room Shared Wall 
- Room Size Hierarchy 

## Soft Constraints 
- Bathroom Location 
- Compact Layout
- Layout Dead Space
- Recessed Facade Penalty
- Room Shared Wall Soft Refine
- See Facade Alignment Penalty
- See Facade Depth Penalty
- Seed Layout Hints
- Soft Room Adjacency


# Group By 
## fpgr_generate
- Uses `fpgr_p_generate.FloorPlanGenerator` -> `FpgrCore.solve()` with:
  - `include_constraint_b_soft=False`
  - `include_constraint_a_soft=False`
  - `include_constraint_c_soft=False`
  - `include_constraint_d_soft=False`
  - `include_constraint_shared_wall_soft=False`
- Hard constraints applied (from `fpgr_core`):
  - basic constraints (`constraints/hard/basic_constraints.py`)
  - envelope staircase (`constraints/hard/envelope_staircase.py`)
  - floor area coverage (`constraints/hard/floor_area_coverage.py`)
  - hallway constraints (`constraints/hard/hallway_constraints.py`)
  - room adjacency hard (`constraints/hard/room_adjacency_hard.py`)
  - room location hard (`constraints/hard/room_location_hard.py`)
  - room shared wall hard (`constraints/hard/room_shared_wall_constraints.py`)
  - room size hierarchy (`constraints/hard/room_size_hierarchy_constraints.py`)
- Soft constraints that may execute regardless of A/B/C/D flags:
  - compact layout center proximity (`constraints/soft/compact_layout.py`)
  - bathroom location preference (`constraints/soft/bathroom_location_preference.py`)
  - soft room adjacency (`constraints/soft/soft_room_adjacency.py`)
  - seed layout hints are skipped (no seed layout in profile 1)

## fpgr_refine_1
- Uses `fpgr_p_refine_1.run_refine_profile_1()` -> `FpgrCore.solve()` with:
  - `include_constraint_b_soft=True`
  - `include_constraint_a_soft=True`
  - `include_constraint_c_soft=True`
  - `include_constraint_d_soft=True`
  - `include_constraint_shared_wall_soft=True`
- All hard constraints are still applied (same list as fpgr_generate).
- Soft constraints active in refine profile:
  - layout dead space penalty (`constraints/soft/layout_dead_space_penalty.py`) [A]
  - seed facade depth penalty (`constraints/soft/seed_facade_depth_penalty.py`) [B]
  - seed facade alignment penalty (`constraints/soft/seed_facade_alignment_penalty.py`) [C]
  - recessed facade penalty (`constraints/soft/recessed_facade_penalty.py`) [D]
  - shared wall soft refine (`constraints/soft/room_shared_wall_soft_refine.py`)
  - plus those from generate profile if enabled (compact layout, bathroom location, soft room adjacency, seed layout hints)

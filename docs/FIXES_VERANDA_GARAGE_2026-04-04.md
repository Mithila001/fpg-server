# Veranda & Garage Placement Fixes - April 4, 2026

## Issues Fixed

### 1. verandaOutdoorSpace Not Persisted to Results
**Problem:** verandaOutdoorSpace rooms were created inside the constraint function but never added to the room list, so they never appeared in final solver solutions or scoring.

**Root Cause:** The constraint function created auxiliary room objects locally but didn't return them, and fpgr_core.py wasn't capturing any return value.

**Solution:**
- Modified `add_open_area_placement_constraints()` return type from `None` to `List[Room]`
- Track created auxiliary rooms in local list
- Return the list at end of function
- Updated fpgr_core.py to capture returned rooms and extend self.rooms before solving

**Files Changed:**
- `app/algorithms/fpg_rooms/constraints/hard/open_area_placement.py`
- `app/algorithms/fpg_rooms/fpgr_core.py` (line ~196)

**Result:** verandaOutdoorSpace now appears in:
- Solution JSON output
- Solver room list used for scoring
- Final layout plotters

---

### 2. Garage Placed at Unrealistic Center Front
**Problem:** Garage was only constrained to y=0 (front), but could be placed anywhere horizontally on the front boundary, resulting in unrealistic center-front positioning.

**Expected Behavior:** Garage should be anchored to either front-left corner or front-right corner (typical parking behind/beside house).

**Solution:**
- Added BoolVar `garage_at_left_corner` to force two branches
- Left branch: `garage.x ≤ 10` (clamped to left side)
- Right branch: `garage.x_end ≥ land_width - 10` (clamped to right side)
- Solver chooses one branch, preventing center placement

**File Changed:**
- `app/algorithms/fpg_rooms/constraints/hard/open_area_placement.py`

**Result:** Garage now positioned realistically at either corner, never center.

---

## Verification

### Unit Tests
All constraint tests pass:
```bash
pytest test/unit/test_open_area_placement_constraint.py test/unit/test_room_location_hard.py -v
# Result: 7 passed
```

### Type Checking
Return type annotation verified:
```bash
python3 -c "from app.algorithms.fpg_rooms.constraints.hard.open_area_placement import add_open_area_placement_constraints; print(add_open_area_placement_constraints.__annotations__['return'])"
# Result: List[Room]
```

### Integration Check
Run API endpoint to verify verandaOutdoorSpace appears in final output:
```bash
POST http://localhost:8000/algorithms/format/v2
# Check response JSON for "verandaOutdoorSpace" room type entries
```

---

## Coordinate System Reference
Refer to [docs/COORDINATE_SYSTEM.md](COORDINATE_SYSTEM.md) for veranda/garage positioning rules:
- **Front (y=0):** Street-facing entrance/access
- **Back (y=max):** Interior
- **Left (x=0):** Viewer's left
- **Right (x=max):** Viewer's right

---

## Next Steps (Optional)
- Update post-processing to handle verandaOutdoorSpace conversion to empty space if desired
- Adjust garage corner tolerance (currently ±10 units) if needed
- Monitor scoring impact of verandaOutdoorSpace inclusion

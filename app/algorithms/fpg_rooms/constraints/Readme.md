## File Naming Convention

- Everything at `app/algorithms/fpg_rooms/constraints/soft` will have `soft_` file name prefix. 
- Everything at `app/algorithms/fpg_rooms/constraints/hard` will have `hard_` file name prefix. 
- If the constraint relay on seeding, then additional `seed_` prefix wil be added to that file.

## Coordinate System

**IMPORTANT:** All constraints use a consistent coordinate system. See [docs/COORDINATE_SYSTEM.md](../../docs/COORDINATE_SYSTEM.md) for detailed definitions of:
- Front / Back / Left / Right directional mappings
- X and Y axis conventions  
- Room wall definitions
- Special rules for veranda, garage, and verandaOutdoorSpace

**Quick Reference:**
- **Front** = y=0 (bottom of screen, street-facing)
- **Back** = y≥ y_max (top of screen, interior)
- **Left** = x=0
- **Right** = x=max
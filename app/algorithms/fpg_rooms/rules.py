from .types.room import FpgRequirements, RoomData
from app.core.fpg_rooms.config_fpg import DEFAULT_MIN_W, DEFAULT_MIN_H, DEFAULT_MAX_W, DEFAULT_MAX_H

# normalization rules for requirement objects
#TODO: Check if this needed. Looks like useless
def normalize_requirements(req: FpgRequirements) -> FpgRequirements:
    """Return a copy of ``req`` where any missing min/max dimensions are filled.

    - ``min_w``/``min_h`` default to DEFAULT_MIN_W/DEFAULT_MIN_H when ``None`` or empty string.
    - ``max_w``/``max_h`` default to DEFAULT_MAX_W/DEFAULT_MAX_H when ``None`` or empty string.

    We operate on the room list and preserve the original ``config`` object.
    """
    normalized_rooms: list[RoomData] = []
    for r in req.rooms:
        # duck‑type against falsy values, but treat 0 as valid
        min_w = r.min_w if r.min_w not in (None, "") else DEFAULT_MIN_W
        min_h = r.min_h if r.min_h not in (None, "") else DEFAULT_MIN_H
        max_w = r.max_w if r.max_w not in (None, "") else DEFAULT_MAX_W
        max_h = r.max_h if r.max_h not in (None, "") else DEFAULT_MAX_H
        normalized_rooms.append(
            RoomData(r.name, r.type, min_w, min_h, max_w, max_h)
        )

    # Preserve relation constraints when normalizing.
    relation_constraints = getattr(req, "relation_constraints", None)
    return FpgRequirements(
        rooms=normalized_rooms,
        config=req.config,
        relation_constraints=relation_constraints,
    )

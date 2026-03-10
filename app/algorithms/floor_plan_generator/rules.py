
from .types.room import FpgRequirements, RoomData

MAX_WIDTH = 100
MAX_HEIGHT = 100
# normalization rules for requirement objects
def normalize_requirements(req: FpgRequirements) -> FpgRequirements:
    """Return a copy of ``req`` where any missing min/max dimensions are filled.

    - ``min_w``/``min_h`` default to 0 when ``None`` or empty string.
    - ``max_w``/``max_h`` default to MAX_WIDTH/MAX_HEIGHT when ``None`` or empty string.

    We operate on the room list and preserve the original ``config`` object.
    """
    normalized_rooms: list[RoomData] = []
    for r in req.rooms:
        # duck‑type against falsy values, but treat 0 as valid
        min_w = r.min_w if r.min_w not in (None, "") else 0
        min_h = r.min_h if r.min_h not in (None, "") else 0
        max_w = r.max_w if r.max_w not in (None, "") else MAX_WIDTH
        max_h = r.max_h if r.max_h not in (None, "") else MAX_HEIGHT
        normalized_rooms.append(
            RoomData(r.name, r.type, min_w, min_h, max_w, max_h)
        )
    return FpgRequirements(rooms=normalized_rooms, config=req.config)

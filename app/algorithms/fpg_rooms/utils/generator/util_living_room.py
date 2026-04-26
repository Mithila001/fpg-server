from ...solver_models.room import Room
from ....types import FpgRequirements


def _get_living_room_requirements(
    requirements: FpgRequirements,
) -> tuple[int, int, int, int]:
    for room in requirements.rooms:
        if room.type == "livingRoom":
            return int(room.min_w), int(room.min_h), int(room.max_w), int(room.max_h)

    raise ValueError("LivingRoom requirement is missing from normalized requirements")


def generate_living_room(requirements: FpgRequirements) -> Room:
    """Create the mandatory living room based on normalized requirements."""
    min_w, min_h, max_w, max_h = _get_living_room_requirements(requirements)

    living_room = Room(
        "livingRoom1",
        min_w,
        min_h,
        max_w,
        max_h,
        "livingRoom",
    )

    return living_room

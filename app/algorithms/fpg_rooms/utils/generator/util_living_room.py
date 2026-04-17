from ...solver_models.room import Room
from app.core.fpg_rooms.config_fpg import (
    LIVING_ROOM_MIN_HEIGHT,
    LIVING_ROOM_MIN_WIDTH,
)
from ...types.room import FpgRequirements


def generate_living_room(requirements: FpgRequirements) -> Room:
    """Create the mandatory living room based on normalized requirements."""
    floor_width = requirements.config.floor_plan_width
    floor_height = requirements.config.floor_plan_height

    living_room = Room(
        "Living Room",
        LIVING_ROOM_MIN_WIDTH,
        LIVING_ROOM_MIN_HEIGHT,
        int(floor_width * 0.5),
        int(floor_height * 0.5),
        "livingRoom",
    )

    return living_room

from ...solver_models.room import Room
from ...types.room import FpgRequirements


def generate_living_room(requirements: FpgRequirements) -> Room:
    """Create the mandatory living room based on normalized requirements."""
    floor_width = requirements.config.floor_plan_width
    floor_height = requirements.config.floor_plan_height

    living_room = Room(
        "Living Room",
        0,
        0,
        int(floor_width),
        int(floor_height),
        "livingRoom",
    )

    return living_room

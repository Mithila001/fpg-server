from typing import List

from ...solver_models.room import Room
from ...types.room import FpgRequirements


def generate_hallway_rooms(requirements: FpgRequirements) -> List[Room]:
    """Create hallway rooms based on normalized requirements."""
    hallway_count = max(0, int(requirements.config.hallway_count))
    floor_width = requirements.config.floor_plan_width
    floor_height = requirements.config.floor_plan_height

    if hallway_count <= 0:
        return []
    """Create hallway rooms based on configured hallway count."""
    if hallway_count <= 0:
        return []

    max_w = max(5, int(floor_width * 0.8))
    max_h = max(5, int(floor_height * 0.8))

    hallways: list[Room] = []
    for i in range(hallway_count):
        hallways.append(
            Room(
                f"hallway{i + 1}",
                5,
                5,
                max_w,
                max_h,
                "hallway",
            )
        )

    # Keep config aligned with generated hallway count
    requirements.config.hallway_count = len(hallways)
    return hallways

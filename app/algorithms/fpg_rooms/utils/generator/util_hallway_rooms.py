from copy import deepcopy
from typing import List

from ...solver_models.room import Room
from app.core.fpg_rooms.config_fpg import (
    HALLWAY_GENERATOR_MIN_HEIGHT,
    HALLWAY_GENERATOR_MIN_WIDTH,
    HALLWAY_RULE_TARGET_ROOM_TYPES,
)
from ....types import FpgRequirements


def prepare_requirements_for_hallway_rules(
    requirements: FpgRequirements,
) -> FpgRequirements:
    """Return one copied requirements object updated with hallway-related relation rules.

    If hallway_count > 0, for hard_OR rules on bedroom/kitchen/bathroom,
    ensure related_room includes both livingRoom and hallway.
    """
    updated_requirements = deepcopy(requirements)
    hallway_count = max(0, int(updated_requirements.config.hallway_count))
    if hallway_count <= 0:
        return updated_requirements

    relation_constraints = updated_requirements.relation_constraints or []
    target_room_types = HALLWAY_RULE_TARGET_ROOM_TYPES
    for relation in relation_constraints:
        room_type = None
        constraint_level = None
        related_room_raw = None

        if isinstance(relation, dict):
            room_type = relation.get("room_type")
            constraint_level = relation.get("constraint_level")
            related_room_raw = relation.get("related_room")
        else:
            room_type = getattr(relation, "room_type", None)
            constraint_level = getattr(relation, "constraint_level", None)
            related_room_raw = getattr(relation, "related_room", None)

        room_type_norm = str(room_type or "").strip().lower()
        constraint_level_norm = str(constraint_level or "").strip().lower()

        if (
            constraint_level_norm != "hard_or"
            or room_type_norm not in target_room_types
        ):
            continue

        related_room: list[str] = []
        if isinstance(related_room_raw, list):
            related_room = [str(item) for item in related_room_raw]

        if "livingRoom" not in related_room:
            related_room.append("livingRoom")
        if "hallway" not in related_room:
            related_room.append("hallway")

        if isinstance(relation, dict):
            relation["related_room"] = related_room
        else:
            setattr(relation, "related_room", related_room)

    return updated_requirements


def generate_hallway_rooms(requirements: FpgRequirements) -> List[Room]:
    """Create hallway rooms based on normalized requirements."""
    hallway_count = max(0, int(requirements.config.hallway_count))
    floor_width = requirements.config.floor_plan_width
    floor_height = requirements.config.floor_plan_height

    if hallway_count <= 0:
        return []

    max_w = max(HALLWAY_GENERATOR_MIN_WIDTH, int(floor_width * 0.8))
    max_h = max(HALLWAY_GENERATOR_MIN_HEIGHT, int(floor_height * 0.8))

    hallways: list[Room] = []
    for i in range(hallway_count):
        hallways.append(
            Room(
                f"hallway{i + 1}",
                HALLWAY_GENERATOR_MIN_WIDTH,
                HALLWAY_GENERATOR_MIN_HEIGHT,
                max_w,
                max_h,
                "hallway",
            )
        )

    # Keep config aligned with generated hallway count
    requirements.config.hallway_count = len(hallways)
    return hallways

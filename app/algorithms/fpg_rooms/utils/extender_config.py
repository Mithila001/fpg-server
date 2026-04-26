"""Configuration for extender rooms.

Extender rooms are optional room extensions attached to parent rooms.
They are soft-optimized during refinement to fill empty spaces adjacent to parent rooms.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExtenderDef:
    """Definition of an extender room configuration.

    Attributes:
        name: Unique identifier for this extender room (e.g., 'living_room_ext').
        parent_room_name: Name of the parent room to which this extender attaches.
        min_w: Minimum width (cm). If 0, extender is allowed to be inactive (w=0).
        min_h: Minimum height (cm). If 0, extender is allowed to be inactive (h=0).
        max_w: Maximum width (cm) when active.
        max_h: Maximum height (cm) when active.
    """

    name: str
    parent_room_name: str
    min_w: int
    min_h: int
    max_w: int
    max_h: int


# Hardcoded extender configurations per parent room type.
# For now, only living_room has one extender defined.

LIVING_ROOM_EXTENDER_CONFIGS: list[ExtenderDef] = [
    ExtenderDef(
        name="livingRoom_ext",
        parent_room_name="livingRoom",
        min_w=0,  # 0 allows solver to deactivate (w=0, h=0 feasible)
        min_h=0,
        max_w=20,
        max_h=20,
    ),
]

# Map of parent room types to their extender configurations.
EXTENDER_CONFIGS_BY_PARENT: dict[str, list[ExtenderDef]] = {
    "livingRoom": LIVING_ROOM_EXTENDER_CONFIGS,
}


def get_extenders_for_parent(parent_room_name: str) -> list[ExtenderDef]:
    """Retrieve extender configurations for a given parent room name.

    Args:
        parent_room_name: Name of the parent room (e.g., 'livingRoom').

    Returns:
        List of ExtenderDef configurations for that parent. Empty if no extenders defined.
    """
    return EXTENDER_CONFIGS_BY_PARENT.get(parent_room_name, [])

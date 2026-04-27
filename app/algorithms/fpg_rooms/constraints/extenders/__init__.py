"""Extender room constraints and utilities.

Extender rooms are optional room extensions attached to parent rooms.
This module provides hard constraints for their placement.
"""

from .extender_wall_attachment import add_extender_wall_attachment_constraint
from .extender_room_size import add_extender_room_size_constraint

__all__ = [
    "add_extender_wall_attachment_constraint",
    "add_extender_room_size_constraint",
]

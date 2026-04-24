"""Extender room constraints and utilities.

Extender rooms are optional room extensions attached to parent rooms.
This module provides hard and soft constraints for their placement.
"""
from .extender_wall_attachment import add_extender_wall_attachment_constraint
from .extender_placement_soft import add_extender_placement_soft_penalty

__all__ = [
    "add_extender_wall_attachment_constraint",
    "add_extender_placement_soft_penalty",
]

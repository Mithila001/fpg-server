"""Compatibility shim for floor plan config values."""

from app.core.config_fpg import (
    FLOOR_WIDTH,
    FLOOR_HEIGHT,
    MIN_COVERAGE,
    MAX_ASPECT_RATIO_HEIGHT,
    MAX_ASPECT_RATIO_WIDTH,
    HALLWAY_WIDTH,
    HALLWAY_MIN_LENGTH,
)

__all__ = [
    "FLOOR_WIDTH",
    "FLOOR_HEIGHT",
    "MIN_COVERAGE",
    "MAX_ASPECT_RATIO_HEIGHT",
    "MAX_ASPECT_RATIO_WIDTH",
    "HALLWAY_WIDTH",
    "HALLWAY_MIN_LENGTH",
]


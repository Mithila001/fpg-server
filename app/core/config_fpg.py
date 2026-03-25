"""Floor plan generation config (shared)."""

# Floor Dimensions (default)
FLOOR_WIDTH = 200
FLOOR_HEIGHT = 200

# Maximum allowed aspect ratio for rooms
MAX_ASPECT_RATIO_HEIGHT = 10
MAX_ASPECT_RATIO_WIDTH = 16

# Minimum floor area coverage (50%)
MIN_COVERAGE = 0.5

# Hallway dimensions
# Fixed narrow dimension — the solver enforces exactly this value for
# whichever of width/height is the "short" side.
HALLWAY_WIDTH = 5
# Minimum length of the long side (the solver may extend it further).
HALLWAY_MIN_LENGTH = 5

__all__ = [
    "FLOOR_WIDTH",
    "FLOOR_HEIGHT",
    "MAX_ASPECT_RATIO_HEIGHT",
    "MAX_ASPECT_RATIO_WIDTH",
    "MIN_COVERAGE",
    "HALLWAY_WIDTH",
    "HALLWAY_MIN_LENGTH",
]

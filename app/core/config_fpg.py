"""Floor plan generation config (shared)."""

# Floor Dimensions (default)
FLOOR_WIDTH = 200
FLOOR_HEIGHT = 200

# Maximum allowed aspect ratio for rooms
MAX_ASPECT_RATIO_HEIGHT = 10
MAX_ASPECT_RATIO_WIDTH = 16

# Minimum floor area coverage (50%)
MIN_COVERAGE = 0.5

# Floor-plan scoring weights
SCORE_WEIGHTS = {
    "coverage": 0.40,
    "rectangularity": 0.35,
    "empty_space": 0.25,
}

# Envelope/staircase settings
ENVELOPE_ENABLED = True
ENVELOPE_MIN_GAP = 5
ENVELOPE_MAX_GAP = 15
ENVELOPE_EXCLUDE_TYPES = ["hallway"]
ENVELOPE_APPLY_SIDES = ["left", "right", "top", "bottom"]

# Adjacency constraint settings
DEFAULT_ADJACENCY_MIN_OVERLAP = 1

# Room location/bathroom preferences
BATHROOM_LOCATION_WEIGHT = 1

# Room size hierarchy (% of living room area)
ROOM_SIZE_HIERARCHY = {
    "bedroom": (50, 70),
    "kitchen": (40, 50),
    "bathroom": (15, 30),
}

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
    "SCORE_WEIGHTS",
    "DEFAULT_ADJACENCY_MIN_OVERLAP",
    "ENVELOPE_ENABLED",
    "ENVELOPE_MIN_GAP",
    "ENVELOPE_MAX_GAP",
    "ENVELOPE_EXCLUDE_TYPES",
    "ENVELOPE_APPLY_SIDES",
    "BATHROOM_LOCATION_WEIGHT",
    "ROOM_SIZE_HIERARCHY",
    "HALLWAY_WIDTH",
    "HALLWAY_MIN_LENGTH",
]

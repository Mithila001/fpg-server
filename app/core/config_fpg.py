"""Floor plan generation config (shared)."""

# Floor Dimensions (default)
FLOOR_WIDTH = 1000
FLOOR_HEIGHT = 1500

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
ENVELOPE_MIN_GAP = 50
ENVELOPE_MAX_GAP = 200
ENVELOPE_EXCLUDE_TYPES = ["hallway"]
ENVELOPE_APPLY_SIDES = ["left", "right", "top", "bottom"]

# Adjacency constraint settings
DEFAULT_ADJACENCY_MIN_OVERLAP = 100
GENERATOR_ADJACENCY_MIN_OVERLAP = 100

# Room location/bathroom preferences
BATHROOM_LOCATION_WEIGHT = 1

# Default room size bounds used in normalization/fallback payloads
DEFAULT_MIN_W = 120
DEFAULT_MIN_H = 5
DEFAULT_MAX_W = 700
DEFAULT_MAX_H = 700

# Room size hierarchy (% of living room area)
ROOM_SIZE_HIERARCHY = {
    "bedroom": (50, 70),
    "kitchen": (40, 50),
    "bathroom": (15, 30),
}

# Default solver/optuna execution settings
DEFAULT_ROOM_DIMENSION = 700
DEFAULT_OPTUNA_TRIALS = 10
DEFAULT_OPTUNA_STORAGE_ENABLED = False
DEFAULT_OPTUNA_STORAGE_URL = "sqlite:///optuna_fpg.db"

# Default generator config
DEFAULT_ASPECT_RATIO_MAX = 16.0
DEFAULT_ASPECT_RATIO_MIN = 0.0
DEFAULT_HALLWAY_COUNT = 1
DEFAULT_SOLVER_MAX_TIME_SECONDS = 1

# Hallway dimensions
# Fixed narrow dimension — the solver enforces exactly this value for
# whichever of width/height is the "short" side.
HALLWAY_WIDTH = 100
# Minimum length of the long side (the solver may extend it further).
HALLWAY_MIN_LENGTH = 100

__all__ = [
    "FLOOR_WIDTH",
    "FLOOR_HEIGHT",
    "MAX_ASPECT_RATIO_HEIGHT",
    "MAX_ASPECT_RATIO_WIDTH",
    "MIN_COVERAGE",
    "SCORE_WEIGHTS",
    "DEFAULT_ADJACENCY_MIN_OVERLAP",
    "GENERATOR_ADJACENCY_MIN_OVERLAP",
    "ENVELOPE_ENABLED",
    "ENVELOPE_MIN_GAP",
    "ENVELOPE_MAX_GAP",
    "ENVELOPE_EXCLUDE_TYPES",
    "ENVELOPE_APPLY_SIDES",
    "BATHROOM_LOCATION_WEIGHT",
    "DEFAULT_MIN_W",
    "DEFAULT_MIN_H",
    "DEFAULT_MAX_W",
    "DEFAULT_MAX_H",
    "ROOM_SIZE_HIERARCHY",
    "DEFAULT_ROOM_DIMENSION",
    "DEFAULT_OPTUNA_TRIALS",
    "DEFAULT_OPTUNA_STORAGE_ENABLED",
    "DEFAULT_OPTUNA_STORAGE_URL",
    "DEFAULT_ASPECT_RATIO_MAX",
    "DEFAULT_ASPECT_RATIO_MIN",
    "DEFAULT_HALLWAY_COUNT",
    "DEFAULT_SOLVER_MAX_TIME_SECONDS",
    "HALLWAY_WIDTH",
    "HALLWAY_MIN_LENGTH",
]

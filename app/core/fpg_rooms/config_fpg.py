"""Floor plan generation config (shared)."""

# Floor Dimensions (default)
FLOOR_WIDTH = 100
FLOOR_HEIGHT = 150

# Minimum floor dimensions constraint
MIN_FLOOR_WIDTH = 50
MIN_FLOOR_HEIGHT = 50

# Minimum floor area buffer (added to total min room area for feasibility check)
MIN_FLOOR_AREA_BUFFER = 500

# Maximum allowed aspect ratio for rooms
MAX_ASPECT_RATIO_HEIGHT = 10
MAX_ASPECT_RATIO_WIDTH = 16

# Minimum floor area coverage (50%)
MIN_COVERAGE = 0.5

# Safety buffer used in pre-validation feasibility checks
SAFETY_BUFFER = 100.0

# Floor-plan scoring weights
SCORE_WEIGHTS = {
    "coverage": 0.40,
    "rectangularity": 0.35,
    "empty_space": 0.25,
}

# Shapely scoring controls
SCORE_GEOMETRY_TOLERANCE = 1e-6
INWARD_POCKET_MAX_LENGTH = 20.0

# Envelope/staircase settings
ENVELOPE_ENABLED = True
ENVELOPE_MIN_GAP = 5
ENVELOPE_MAX_GAP = 20
ENVELOPE_EXCLUDE_TYPES = []  # Non eligible room types for envelope checking
ENVELOPE_APPLY_SIDES = ["left", "right", "top", "bottom"]

# Garage placement settings
GARAGE_SIDE_ANCHOR_THRESHOLD = 20

# Veranda outdoor space bounds
VERANDA_OUTDOOR_SPACE_MIN_W = 1
VERANDA_OUTDOOR_SPACE_MIN_H = 1
VERANDA_OUTDOOR_SPACE_MAX_W = 100
VERANDA_OUTDOOR_SPACE_MAX_H = 100

# Adjacency constraint settings
DEFAULT_ADJACENCY_MIN_OVERLAP = 10  # Default value when no value is given
GENERATOR_ADJACENCY_MIN_OVERLAP = 10  # Actual using value

# Room location/bathroom preferences
BATHROOM_LOCATION_WEIGHT = 1

# Constraint toggles (hard)
CONSTRAINT_HARD_BASIC_GEOMETRY = True
CONSTRAINT_HARD_HALLWAY_RULES = True
CONSTRAINT_HARD_ROOM_SHARED_WALLS = True
CONSTRAINT_HARD_ROOM_ADJACENCY = True
CONSTRAINT_HARD_MINIMUM_AREA_COVERAGE = False
CONSTRAINT_HARD_ROOM_SIZE_HIERARCHY = True
CONSTRAINT_HARD_LIVING_ROOM_LOCATION = False
CONSTRAINT_HARD_VERANDA_PLACEMENT = True
CONSTRAINT_HARD_GARAGE_PLACEMENT = True
CONSTRAINT_HARD_ENVELOPE_STAIRCASE = True
CONSTRAINT_HARD_KITCHEN_HALLWAY_BACK_WALL_SETBACK = True

# Kitchen/hallway back-wall door setback settings
KITCHEN_HALLWAY_BACK_WALL_SETBACK_MIN_GAP = 5
KITCHEN_HALLWAY_BACK_WALL_SETBACK_MAX_GAP = 20

# Constraint toggles (soft)
CONSTRAINT_SOFT_SEED_LAYOUT_HINTS = True
CONSTRAINT_SOFT_ROOM_ADJACENCY_PREFERENCE = True
CONSTRAINT_SOFT_COMPACT_LAYOUT_CENTER_PROXIMITY = True
CONSTRAINT_SOFT_BATHROOM_LOCATION_PREFERENCE = False
CONSTRAINT_SOFT_LAYOUT_DEAD_SPACE_PENALTY = True
CONSTRAINT_SOFT_SEED_FACADE_DEPTH_PENALTY = True
CONSTRAINT_SOFT_SEED_FACADE_ALIGNMENT_PENALTY = True
CONSTRAINT_SOFT_RECESSED_FACADE_PENALTY = True
CONSTRAINT_SOFT_ROOM_SHARED_WALL_REFINE = True

# Extender room constraints (hard and soft)
CONSTRAINT_HARD_EXTENDER_WALL_ATTACHMENT = (
    False  # Disabled by default; enabled only in refine_profile_extender
)

# Soft-constraint tuning constants
SOFT_LAYOUT_DEAD_SPACE_WEIGHT = 12
SOFT_SEED_FACADE_DEPTH_WEIGHT = 25
SOFT_SEED_FACADE_ALIGNMENT_WEIGHT = 8
SOFT_SEED_FACADE_ALIGNMENT_THRESHOLD = 10
SOFT_RECESSED_FACADE_NEAR_BAND = 45
SOFT_RECESSED_FACADE_BASE_THRESHOLD = 10
SOFT_RECESSED_FACADE_SEVERE_THRESHOLD = 20
SOFT_RECESSED_FACADE_BASE_WEIGHT = 45
SOFT_RECESSED_FACADE_SEVERE_WEIGHT = 140
SOFT_RECESSED_FACADE_ATTACH_WEIGHT = 14
SOFT_RECESSED_FACADE_SIDE_GAP_THRESHOLD = 40
SOFT_ROOM_SHARED_WALL_REFINE_WEIGHT = 50

# Default room size bounds used in normalization/fallback payloads
DEFAULT_MIN_W = 12
DEFAULT_MIN_H = 10
DEFAULT_MAX_W = 70
DEFAULT_MAX_H = 70

# Room size hierarchy (% of living room area)
ROOM_SIZE_HIERARCHY = {
    "bedroom": (60, 75),  # Increased from (50, 70)
    "kitchen": (45, 55),  # Tightened from (40, 50)
    "bathroom": (20, 30),  # Refined from (15, 30)
    "attachedBathroom": (20, 25),  # Refined from (15, 30)
    "veranda": (55, 70),  # Lifted from (40, 70)
    "garage": (100, 120),  # Major change: Garage is larger than Living Room
    "diningRoom": (70, 75),  # Major change: Increased from (30, 50)
}

# Room types used by hallway-related generation rules.
HALLWAY_RULE_TARGET_ROOM_TYPES = {"bedroom", "kitchen", "bathroom", "diningRoom"}

# Default solver/optuna execution settings
DEFAULT_ROOM_DIMENSION = 70
DEFAULT_OPTUNA_TRIALS = 20
DEFAULT_OPTUNA_STORAGE_ENABLED = False
DEFAULT_OPTUNA_STUDY_NAME = "FPG_study"
DEFAULT_OPTUNA_STORAGE_URL = "sqlite:///optuna_fpg.db"

# Trial optimization control
MINIMUM_REQUIRED_FPG_SCORE = 90  # Stop trials if score exceeds this
TRIAL_OPTIMIZATION_TIMEOUT_SECONDS = 60  # Hard deadline for all trials
TRIAL_GRAPH_SOLVER_GATE_THRESHOLD = (
    80  # Invoke solver only when graph score reaches this
)

# Optuna search space grid scale
OPTUNA_SEARCH_SPACE_GRID_SCALE = 10  # Reduce search space resolution by this interval

# Default generator config
DEFAULT_ASPECT_RATIO_MAX = 16.0
DEFAULT_ASPECT_RATIO_MIN = 0.0
DEFAULT_HALLWAY_COUNT = 2
DEFAULT_SOLVER_MAX_TIME_SECONDS = 3
WIGGLE_ROOM = 10

# TODO Fix hallway config value duplication
# Hallway dimensions
# Fixed narrow dimension — the solver enforces exactly this value for
# whichever of width/height is the "short" side.
HALLWAY_NARROW_SIDE = 10
# Minimum width/height used when creating hallway rooms.
HALLWAY_GENERATOR_MIN_WIDTH = 10
HALLWAY_GENERATOR_MIN_HEIGHT = 10
# Minimum length of the long side (the solver may extend it further).
HALLWAY_LONG_SIDE_MIN = 10
# Number of hallway walls that must be fully shared with other rooms.
# Default 3 means only one hallway wall may remain as an exterior wall.
HALLWAY_REQUIRED_SHARED_WALLS = 3

# Room types whose relation constraints should not be pruned by template.
NOT_PRUNE_ROOMS = ["livingRoom", "hallway"]

PUBLIC_ROOM_TYPES = ["garage", "kitchen", "diningRoom"]
PRIVATE_ROOM_TYPES = ["bathroom", "bedroom", "attachedBathroom"]


OPTUNA_NODE_PLACEMENT_PRIVATE = ["bedroom", "bathroom", "attachedBathroom"]
OPTUNA_NODE_PLACEMENT_PUBLIC = ["garage", "kitchen", "diningRoom", "livingRoom"]
OPTUNA_NODE_PLACEMENT_FRONT = ["veranda", "garage"]

# Per-type room shared-wall requirements.
# - min_walls/max_walls count fully shared sides.
# - wiggle_pct relaxes minimum shared coverage length across the selected
#   min_walls sides; e.g. 30 means up to 30% uncovered is allowed.
ROOM_SHARED_WALL_RULES = {
    "livingRoom": {"min_walls": 2, "max_walls": 4, "wiggle_pct": 10},
    "bathroom": {"min_walls": 2, "max_walls": 4, "wiggle_pct": 5},
    "bedroom": {"min_walls": 2, "max_walls": 4, "wiggle_pct": 10},
    "kitchen": {"min_walls": 2, "max_walls": 4, "wiggle_pct": 10},
    "attachedBathroom": {"min_walls": 2, "max_walls": 4, "wiggle_pct": 0},
    "veranda": {"min_walls": 2, "max_walls": 3, "wiggle_pct": 10},
    "garage": {"min_walls": 2, "max_walls": 3, "wiggle_pct": 10},
    "diningRoom": {"min_walls": 2, "max_walls": 4, "wiggle_pct": 10},
}
# Refinement phase shared-wall rules (tighter minimum requirements for refine_1).
# Applied as soft constraint with penalties for violations.
ROOM_SHARED_WALL_RULES_REFINE = {
    "livingRoom": {"min_walls": 2, "max_walls": 4, "wiggle_pct": 10},
    "bathroom": {"min_walls": 2, "max_walls": 4, "wiggle_pct": 5},
    "bedroom": {"min_walls": 2, "max_walls": 4, "wiggle_pct": 10},
    "kitchen": {"min_walls": 2, "max_walls": 4, "wiggle_pct": 10},
    "attachedBathroom": {"min_walls": 2, "max_walls": 4, "wiggle_pct": 0},
    "veranda": {"min_walls": 2, "max_walls": 3, "wiggle_pct": 10},
    "garage": {"min_walls": 2, "max_walls": 3, "wiggle_pct": 10},
    "diningRoom": {"min_walls": 2, "max_walls": 4, "wiggle_pct": 10},
}

__all__ = [
    "FLOOR_WIDTH",
    "FLOOR_HEIGHT",
    "MIN_FLOOR_WIDTH",
    "MIN_FLOOR_HEIGHT",
    "MIN_FLOOR_AREA_BUFFER",
    "MAX_ASPECT_RATIO_HEIGHT",
    "MAX_ASPECT_RATIO_WIDTH",
    "MIN_COVERAGE",
    "SCORE_WEIGHTS",
    "SCORE_GEOMETRY_TOLERANCE",
    "INWARD_POCKET_MAX_LENGTH",
    "DEFAULT_ADJACENCY_MIN_OVERLAP",
    "GENERATOR_ADJACENCY_MIN_OVERLAP",
    "ENVELOPE_ENABLED",
    "ENVELOPE_MIN_GAP",
    "ENVELOPE_MAX_GAP",
    "ENVELOPE_EXCLUDE_TYPES",
    "ENVELOPE_APPLY_SIDES",
    "BATHROOM_LOCATION_WEIGHT",
    "CONSTRAINT_HARD_BASIC_GEOMETRY",
    "CONSTRAINT_HARD_HALLWAY_RULES",
    "CONSTRAINT_HARD_ROOM_SHARED_WALLS",
    "CONSTRAINT_HARD_ROOM_ADJACENCY",
    "CONSTRAINT_HARD_MINIMUM_AREA_COVERAGE",
    "CONSTRAINT_HARD_ROOM_SIZE_HIERARCHY",
    "CONSTRAINT_HARD_LIVING_ROOM_LOCATION",
    "CONSTRAINT_HARD_VERANDA_PLACEMENT",
    "CONSTRAINT_HARD_GARAGE_PLACEMENT",
    "CONSTRAINT_HARD_ENVELOPE_STAIRCASE",
    "CONSTRAINT_HARD_KITCHEN_HALLWAY_BACK_WALL_SETBACK",
    "KITCHEN_HALLWAY_BACK_WALL_SETBACK_MIN_GAP",
    "KITCHEN_HALLWAY_BACK_WALL_SETBACK_MAX_GAP",
    "CONSTRAINT_SOFT_SEED_LAYOUT_HINTS",
    "CONSTRAINT_SOFT_ROOM_ADJACENCY_PREFERENCE",
    "CONSTRAINT_SOFT_COMPACT_LAYOUT_CENTER_PROXIMITY",
    "CONSTRAINT_SOFT_BATHROOM_LOCATION_PREFERENCE",
    "CONSTRAINT_SOFT_LAYOUT_DEAD_SPACE_PENALTY",
    "CONSTRAINT_SOFT_SEED_FACADE_DEPTH_PENALTY",
    "CONSTRAINT_SOFT_SEED_FACADE_ALIGNMENT_PENALTY",
    "CONSTRAINT_SOFT_RECESSED_FACADE_PENALTY",
    "CONSTRAINT_SOFT_ROOM_SHARED_WALL_REFINE",
    "SOFT_LAYOUT_DEAD_SPACE_WEIGHT",
    "SOFT_SEED_FACADE_DEPTH_WEIGHT",
    "SOFT_SEED_FACADE_ALIGNMENT_WEIGHT",
    "SOFT_SEED_FACADE_ALIGNMENT_THRESHOLD",
    "SOFT_RECESSED_FACADE_NEAR_BAND",
    "SOFT_RECESSED_FACADE_BASE_THRESHOLD",
    "SOFT_RECESSED_FACADE_SEVERE_THRESHOLD",
    "SOFT_RECESSED_FACADE_BASE_WEIGHT",
    "SOFT_RECESSED_FACADE_SEVERE_WEIGHT",
    "SOFT_RECESSED_FACADE_ATTACH_WEIGHT",
    "SOFT_RECESSED_FACADE_SIDE_GAP_THRESHOLD",
    "SOFT_ROOM_SHARED_WALL_REFINE_WEIGHT",
    "DEFAULT_MIN_W",
    "DEFAULT_MIN_H",
    "DEFAULT_MAX_W",
    "DEFAULT_MAX_H",
    "ROOM_SIZE_HIERARCHY",
    "DEFAULT_ROOM_DIMENSION",
    "DEFAULT_OPTUNA_TRIALS",
    "DEFAULT_OPTUNA_STORAGE_ENABLED",
    "DEFAULT_OPTUNA_STORAGE_URL",
    "MINIMUM_REQUIRED_FPG_SCORE",
    "TRIAL_OPTIMIZATION_TIMEOUT_SECONDS",
    "TRIAL_GRAPH_SOLVER_GATE_THRESHOLD",
    "OPTUNA_SEARCH_SPACE_GRID_SCALE",
    "DEFAULT_ASPECT_RATIO_MAX",
    "DEFAULT_ASPECT_RATIO_MIN",
    "DEFAULT_HALLWAY_COUNT",
    "DEFAULT_SOLVER_MAX_TIME_SECONDS",
    "WIGGLE_ROOM",
    "SAFETY_BUFFER",
    "GARAGE_SIDE_ANCHOR_THRESHOLD",
    "HALLWAY_RULE_TARGET_ROOM_TYPES",
    "VERANDA_OUTDOOR_SPACE_MIN_W",
    "VERANDA_OUTDOOR_SPACE_MIN_H",
    "VERANDA_OUTDOOR_SPACE_MAX_W",
    "VERANDA_OUTDOOR_SPACE_MAX_H",
    "HALLWAY_NARROW_SIDE",
    "HALLWAY_GENERATOR_MIN_WIDTH",
    "HALLWAY_GENERATOR_MIN_HEIGHT",
    "HALLWAY_LONG_SIDE_MIN",
    "HALLWAY_REQUIRED_SHARED_WALLS",
    "NOT_PRUNE_ROOMS",
    "ROOM_SHARED_WALL_RULES",
    "ROOM_SHARED_WALL_RULES_REFINE",
    "PRIVATE_ROOM_TYPES",
    "PUBLIC_ROOM_TYPES",
    "OPTUNA_NODE_PLACEMENT_PRIVATE",
    "OPTUNA_NODE_PLACEMENT_PUBLIC",
    "OPTUNA_NODE_PLACEMENT_FRONT",
]

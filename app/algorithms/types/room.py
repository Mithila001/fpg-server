from dataclasses import dataclass, field
from typing import Any
from app.core.fpg_rooms.config_fpg import (
    CONSTRAINT_HARD_BASIC_GEOMETRY,
    CONSTRAINT_HARD_ENVELOPE_STAIRCASE,
    CONSTRAINT_HARD_HALLWAY_RULES,
    CONSTRAINT_HARD_LIVING_ROOM_LOCATION,
    CONSTRAINT_HARD_MINIMUM_AREA_COVERAGE,
    CONSTRAINT_HARD_ROOM_ADJACENCY,
    CONSTRAINT_HARD_ROOM_SHARED_WALLS,
    CONSTRAINT_HARD_ROOM_SIZE_HIERARCHY,
    CONSTRAINT_SOFT_BATHROOM_LOCATION_PREFERENCE,
    CONSTRAINT_SOFT_COMPACT_LAYOUT_CENTER_PROXIMITY,
    CONSTRAINT_SOFT_LAYOUT_DEAD_SPACE_PENALTY,
    CONSTRAINT_SOFT_RECESSED_FACADE_PENALTY,
    CONSTRAINT_SOFT_ROOM_ADJACENCY_PREFERENCE,
    CONSTRAINT_SOFT_SEED_FACADE_ALIGNMENT_PENALTY,
    CONSTRAINT_SOFT_SEED_FACADE_DEPTH_PENALTY,
    CONSTRAINT_SOFT_SEED_LAYOUT_HINTS,
    ENVELOPE_ENABLED,
    ENVELOPE_MIN_GAP,
    ENVELOPE_MAX_GAP,
    ENVELOPE_EXCLUDE_TYPES,
    ENVELOPE_APPLY_SIDES,
    INWARD_POCKET_MAX_LENGTH,
    SCORE_GEOMETRY_TOLERANCE,
)

@dataclass
class RoomData:
    name: str
    type: str
    min_w: int
    min_h: int
    max_w: int
    max_h: int
    is_extender: bool = False
    parent_room_name: str | None = None

@dataclass
class ConfigData:
    min_coverage: float
    max_aspect_ratio: float
    min_aspect_ratio: float
    floor_plan_width: float
    floor_plan_height: float
    hallway_count: int = 1
    envelope_enabled: bool = ENVELOPE_ENABLED
    envelope_min_gap: int = ENVELOPE_MIN_GAP
    envelope_max_gap: int = ENVELOPE_MAX_GAP
    envelope_exclude_types: list[str] = field(default_factory=lambda: ENVELOPE_EXCLUDE_TYPES.copy())
    envelope_apply_sides: list[str] = field(
        default_factory=lambda: ENVELOPE_APPLY_SIDES.copy()
    )
    score_geometry_tolerance: float = SCORE_GEOMETRY_TOLERANCE
    inward_pocket_max_length: float = INWARD_POCKET_MAX_LENGTH
    constraint_hard_basic_geometry: bool = CONSTRAINT_HARD_BASIC_GEOMETRY
    constraint_hard_hallway_rules: bool = CONSTRAINT_HARD_HALLWAY_RULES
    constraint_hard_room_shared_walls: bool = CONSTRAINT_HARD_ROOM_SHARED_WALLS
    constraint_hard_room_adjacency: bool = CONSTRAINT_HARD_ROOM_ADJACENCY
    constraint_hard_minimum_area_coverage: bool = CONSTRAINT_HARD_MINIMUM_AREA_COVERAGE
    constraint_hard_room_size_hierarchy: bool = CONSTRAINT_HARD_ROOM_SIZE_HIERARCHY
    constraint_hard_living_room_location: bool = CONSTRAINT_HARD_LIVING_ROOM_LOCATION
    constraint_hard_envelope_staircase: bool = CONSTRAINT_HARD_ENVELOPE_STAIRCASE
    constraint_soft_seed_layout_hints: bool = CONSTRAINT_SOFT_SEED_LAYOUT_HINTS
    constraint_soft_room_adjacency_preference: bool = CONSTRAINT_SOFT_ROOM_ADJACENCY_PREFERENCE
    constraint_soft_compact_layout_center_proximity: bool = CONSTRAINT_SOFT_COMPACT_LAYOUT_CENTER_PROXIMITY
    constraint_soft_bathroom_location_preference: bool = CONSTRAINT_SOFT_BATHROOM_LOCATION_PREFERENCE
    constraint_soft_layout_dead_space_penalty: bool = CONSTRAINT_SOFT_LAYOUT_DEAD_SPACE_PENALTY
    constraint_soft_seed_facade_depth_penalty: bool = CONSTRAINT_SOFT_SEED_FACADE_DEPTH_PENALTY
    constraint_soft_seed_facade_alignment_penalty: bool = CONSTRAINT_SOFT_SEED_FACADE_ALIGNMENT_PENALTY
    constraint_soft_recessed_facade_penalty: bool = CONSTRAINT_SOFT_RECESSED_FACADE_PENALTY


# Main Param Type
@dataclass
class FpgRequirements:
    rooms: list[RoomData]
    config: ConfigData
    relation_constraints: list[Any] = field(default_factory=list)  # RoomRelationsConstraintBase rows
    initial_point_hints: list[dict[str, Any]] = field(default_factory=list)
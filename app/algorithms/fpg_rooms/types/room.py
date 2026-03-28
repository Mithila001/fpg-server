from dataclasses import dataclass, field
from typing import Any
from app.core.fpg_rooms.config_fpg import (
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


# Main Param Type
@dataclass
class FpgRequirements:
    rooms: list[RoomData]
    config: ConfigData
    relation_constraints: list[Any] = field(default_factory=list)  # RoomRelationsConstraintBase rows
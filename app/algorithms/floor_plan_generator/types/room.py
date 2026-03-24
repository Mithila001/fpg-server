from dataclasses import dataclass, field
from typing import Any

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
    envelope_enabled: bool = True
    envelope_min_gap: int = 5
    envelope_max_gap: int = 15
    envelope_exclude_types: list[str] = field(default_factory=lambda: ["hallway"])
    envelope_apply_sides: list[str] = field(
        default_factory=lambda: ["left", "right", "top", "bottom"]
    )


# Main Param Type
@dataclass
class FpgRequirements:
    rooms: list[RoomData]
    config: ConfigData
    relation_constraints: list[Any] = field(default_factory=list)  # RoomRelationsConstraintBase rows
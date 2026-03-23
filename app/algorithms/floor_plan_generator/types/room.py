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


# Main Param Type
@dataclass
class FpgRequirements:
    rooms: list[RoomData]
    config: ConfigData
    relation_constraints: list[Any] = field(default_factory=list)  # RoomRelationsConstraintBase rows
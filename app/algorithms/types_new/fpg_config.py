# app\algorithms\types_new\fpg_config.py
from dataclasses import dataclass
from .floor_plan_spec import RoomType

# These types are currently not being actively used. There are in configuration phase to layer replace as the better data structure for the project flow.


@dataclass(frozen=True)
class LayoutRuleConfig:
    min_aspect_ratio: float
    max_aspect_ratio: float
    hallway_count: int = 1


@dataclass(frozen=True)
class EnvelopeConfig:
    enabled: bool
    min_gap: float
    max_gap: float
    excluded_room_types: tuple[RoomType, ...] = ()
    apply_sides: tuple[str, ...] = ()


@dataclass(frozen=True)
class HardConstraintConfig:
    basic_geometry: bool = True
    hallway_rules: bool = True
    room_shared_walls: bool = True
    room_adjacency: bool = True
    minimum_area_coverage: bool = True
    room_size_hierarchy: bool = True
    living_room_location: bool = True
    envelope_staircase: bool = True


@dataclass(frozen=True)
class SoftConstraintConfig:
    seed_layout_hints: bool = True
    room_adjacency_preference: bool = True
    compact_layout_center_proximity: bool = True
    bathroom_location_preference: bool = True
    layout_dead_space_penalty: bool = True
    seed_facade_depth_penalty: bool = True
    seed_facade_alignment_penalty: bool = True
    recessed_facade_penalty: bool = True


@dataclass(frozen=True)
class GenerationConfig:
    layout_rules: LayoutRuleConfig
    envelope: EnvelopeConfig
    hard_constraints: HardConstraintConfig
    soft_constraints: SoftConstraintConfig

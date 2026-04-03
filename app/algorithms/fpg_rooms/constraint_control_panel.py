from __future__ import annotations

from dataclasses import dataclass, replace

from app.core.fpg_rooms.config_fpg import (
    CONSTRAINT_HARD_BASIC_GEOMETRY,
    CONSTRAINT_HARD_ENVELOPE_STAIRCASE,
    CONSTRAINT_HARD_HALLWAY_RULES,
    CONSTRAINT_HARD_LIVING_ROOM_LOCATION,
    CONSTRAINT_HARD_MINIMUM_AREA_COVERAGE,
    CONSTRAINT_HARD_OPEN_AREA_PLACEMENT,
    CONSTRAINT_HARD_ROOM_ADJACENCY,
    CONSTRAINT_HARD_ROOM_SHARED_WALLS,
    CONSTRAINT_HARD_ROOM_SIZE_HIERARCHY,
    CONSTRAINT_SOFT_BATHROOM_LOCATION_PREFERENCE,
    CONSTRAINT_SOFT_COMPACT_LAYOUT_CENTER_PROXIMITY,
    CONSTRAINT_SOFT_LAYOUT_DEAD_SPACE_PENALTY,
    CONSTRAINT_SOFT_RECESSED_FACADE_PENALTY,
    CONSTRAINT_SOFT_ROOM_ADJACENCY_PREFERENCE,
    CONSTRAINT_SOFT_ROOM_SHARED_WALL_REFINE,
    CONSTRAINT_SOFT_SEED_FACADE_ALIGNMENT_PENALTY,
    CONSTRAINT_SOFT_SEED_FACADE_DEPTH_PENALTY,
    CONSTRAINT_SOFT_SEED_LAYOUT_HINTS,
)


@dataclass(frozen=True, slots=True)
class ConstraintControlPanel:
    hard_basic_geometry: bool = CONSTRAINT_HARD_BASIC_GEOMETRY
    hard_hallway_rules: bool = CONSTRAINT_HARD_HALLWAY_RULES
    hard_room_shared_walls: bool = CONSTRAINT_HARD_ROOM_SHARED_WALLS
    hard_room_adjacency: bool = CONSTRAINT_HARD_ROOM_ADJACENCY
    hard_minimum_area_coverage: bool = CONSTRAINT_HARD_MINIMUM_AREA_COVERAGE
    hard_room_size_hierarchy: bool = CONSTRAINT_HARD_ROOM_SIZE_HIERARCHY
    hard_living_room_location: bool = CONSTRAINT_HARD_LIVING_ROOM_LOCATION
    hard_open_area_placement: bool = CONSTRAINT_HARD_OPEN_AREA_PLACEMENT
    hard_envelope_staircase: bool = CONSTRAINT_HARD_ENVELOPE_STAIRCASE

    soft_seed_layout_hints: bool = CONSTRAINT_SOFT_SEED_LAYOUT_HINTS
    soft_room_adjacency_preference: bool = CONSTRAINT_SOFT_ROOM_ADJACENCY_PREFERENCE
    soft_compact_layout_center_proximity: bool = CONSTRAINT_SOFT_COMPACT_LAYOUT_CENTER_PROXIMITY
    soft_bathroom_location_preference: bool = CONSTRAINT_SOFT_BATHROOM_LOCATION_PREFERENCE
    soft_layout_dead_space_penalty: bool = CONSTRAINT_SOFT_LAYOUT_DEAD_SPACE_PENALTY
    soft_seed_facade_depth_penalty: bool = CONSTRAINT_SOFT_SEED_FACADE_DEPTH_PENALTY
    soft_seed_facade_alignment_penalty: bool = CONSTRAINT_SOFT_SEED_FACADE_ALIGNMENT_PENALTY
    soft_recessed_facade_penalty: bool = CONSTRAINT_SOFT_RECESSED_FACADE_PENALTY
    soft_room_shared_wall_refine_penalty: bool = CONSTRAINT_SOFT_ROOM_SHARED_WALL_REFINE

    @classmethod
    def generate_profile(cls) -> ConstraintControlPanel:
        return cls(
            soft_seed_layout_hints=False,
            soft_layout_dead_space_penalty=False,
            soft_seed_facade_depth_penalty=False,
            soft_seed_facade_alignment_penalty=False,
            soft_recessed_facade_penalty=False,
            soft_room_shared_wall_refine_penalty=True,
            soft_compact_layout_center_proximity=True,
        )

    @classmethod
    def refine_profile_1(cls) -> ConstraintControlPanel:
        return cls(
            soft_seed_layout_hints=True,
            soft_room_adjacency_preference=True,
            soft_compact_layout_center_proximity=True,
            soft_bathroom_location_preference=True,
            soft_layout_dead_space_penalty=True,
            soft_seed_facade_depth_penalty=True,
            soft_seed_facade_alignment_penalty=True,
            soft_recessed_facade_penalty=True,
            soft_room_shared_wall_refine_penalty=True,
        )

    def with_overrides(self, **changes: bool) -> ConstraintControlPanel:
        return replace(self, **changes)

from __future__ import annotations

import random
from typing import Any

from ortools.sat.python import cp_model

from app.core.fpg_rooms.config_fpg import (
    BATHROOM_LOCATION_WEIGHT,
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
    DEFAULT_SOLVER_MAX_TIME_SECONDS,
    ENVELOPE_APPLY_SIDES,
    ENVELOPE_ENABLED,
    ENVELOPE_EXCLUDE_TYPES,
    ENVELOPE_MAX_GAP,
    ENVELOPE_MIN_GAP,
    GENERATOR_ADJACENCY_MIN_OVERLAP,
    SOFT_LAYOUT_DEAD_SPACE_WEIGHT,
    SOFT_RECESSED_FACADE_ATTACH_WEIGHT,
    SOFT_RECESSED_FACADE_BASE_THRESHOLD,
    SOFT_RECESSED_FACADE_BASE_WEIGHT,
    SOFT_RECESSED_FACADE_NEAR_BAND,
    SOFT_RECESSED_FACADE_SEVERE_THRESHOLD,
    SOFT_RECESSED_FACADE_SEVERE_WEIGHT,
    SOFT_RECESSED_FACADE_SIDE_GAP_THRESHOLD,
    SOFT_SEED_FACADE_ALIGNMENT_THRESHOLD,
    SOFT_SEED_FACADE_ALIGNMENT_WEIGHT,
    SOFT_SEED_FACADE_DEPTH_WEIGHT,
)

from .constraints.hard.basic_constraints import add_basic_constraints
from .constraints.hard.envelope_staircase import add_envelope_staircase_constraints
from .constraints.hard.floor_area_coverage import add_minimum_area_coverage
from .constraints.hard.hallway_constraints import add_hallway_constraints
from .constraints.hard.room_adjacency_hard import apply_hard_room_adjacency_constraints
from .constraints.hard.room_location_hard import add_living_room_bottom_most_constraint
from .constraints.hard.room_shared_wall_constraints import add_room_shared_wall_constraints
from .constraints.hard.room_size_hierarchy_constraints import add_room_size_hierarchy
from .constraints.soft.bathroom_location_preference import build_bathroom_location_preference_penalty
from .constraints.soft.compact_layout import add_center_proximity_objective
from .constraints.soft.layout_dead_space_penalty import build_layout_dead_space_penalty
from .constraints.soft.recessed_facade_penalty import build_recessed_facade_penalty
from .constraints.soft.seed_facade_alignment_penalty import build_seed_facade_alignment_penalty
from .constraints.soft.seed_facade_depth_penalty import build_seed_facade_depth_penalty
from .constraints.soft.seed_layout_hints import apply_seed_layout_hints_with_wiggle
from .constraints.soft.soft_room_adjacency import build_soft_room_adjacency_preference_vars
from .rules import normalize_requirements
from .solver_models.room import Room
from .types.room import FpgRequirements
from .types.room_relations_constraints import RoomRelationsConstraint
from .utils.generator.util_hallway_rooms import (
    generate_hallway_rooms,
    prepare_requirements_for_hallway_rules,
)
from .utils.generator.util_living_room import generate_living_room
from .utils.seed_layout import build_seed_layout_context


class FpgrCore:
    def __init__(self, requirements: FpgRequirements):
        requirements = normalize_requirements(requirements)
        requirements = prepare_requirements_for_hallway_rules(requirements)
        self.requirements = requirements

        self.relation_constraints = self.requirements.relation_constraints

        cfg = requirements.config
        self.floor_plan_width: float = cfg.floor_plan_width
        self.floor_plan_height: float = cfg.floor_plan_height
        self.min_coverage: float = cfg.min_coverage
        self.hallway_count: int = max(0, int(cfg.hallway_count))
        self.envelope_enabled: bool = bool(getattr(cfg, "envelope_enabled", ENVELOPE_ENABLED))
        self.envelope_min_gap: int = max(1, int(getattr(cfg, "envelope_min_gap", ENVELOPE_MIN_GAP)))
        self.envelope_max_gap: int = max(
            self.envelope_min_gap,
            int(getattr(cfg, "envelope_max_gap", ENVELOPE_MAX_GAP)),
        )
        self.envelope_exclude_types: set[str] = {
            str(t).lower() for t in (getattr(cfg, "envelope_exclude_types", ENVELOPE_EXCLUDE_TYPES) or [])
        }
        self.envelope_apply_sides: set[str] = {
            str(side).lower() for side in (getattr(cfg, "envelope_apply_sides", ENVELOPE_APPLY_SIDES) or [])
        }

        self.constraint_hard_basic_geometry = bool(
            getattr(cfg, "constraint_hard_basic_geometry", CONSTRAINT_HARD_BASIC_GEOMETRY)
        )
        self.constraint_hard_hallway_rules = bool(
            getattr(cfg, "constraint_hard_hallway_rules", CONSTRAINT_HARD_HALLWAY_RULES)
        )
        self.constraint_hard_room_shared_walls = bool(
            getattr(cfg, "constraint_hard_room_shared_walls", CONSTRAINT_HARD_ROOM_SHARED_WALLS)
        )
        self.constraint_hard_room_adjacency = bool(
            getattr(cfg, "constraint_hard_room_adjacency", CONSTRAINT_HARD_ROOM_ADJACENCY)
        )
        self.constraint_hard_minimum_area_coverage = bool(
            getattr(cfg, "constraint_hard_minimum_area_coverage", CONSTRAINT_HARD_MINIMUM_AREA_COVERAGE)
        )
        self.constraint_hard_room_size_hierarchy = bool(
            getattr(cfg, "constraint_hard_room_size_hierarchy", CONSTRAINT_HARD_ROOM_SIZE_HIERARCHY)
        )
        self.constraint_hard_living_room_location = bool(
            getattr(cfg, "constraint_hard_living_room_location", CONSTRAINT_HARD_LIVING_ROOM_LOCATION)
        )
        self.constraint_hard_envelope_staircase = bool(
            getattr(cfg, "constraint_hard_envelope_staircase", CONSTRAINT_HARD_ENVELOPE_STAIRCASE)
        )

        self.constraint_soft_seed_layout_hints = bool(
            getattr(cfg, "constraint_soft_seed_layout_hints", CONSTRAINT_SOFT_SEED_LAYOUT_HINTS)
        )
        self.constraint_soft_room_adjacency_preference = bool(
            getattr(cfg, "constraint_soft_room_adjacency_preference", CONSTRAINT_SOFT_ROOM_ADJACENCY_PREFERENCE)
        )
        self.constraint_soft_compact_layout_center_proximity = bool(
            getattr(
                cfg,
                "constraint_soft_compact_layout_center_proximity",
                CONSTRAINT_SOFT_COMPACT_LAYOUT_CENTER_PROXIMITY,
            )
        )
        self.constraint_soft_bathroom_location_preference = bool(
            getattr(
                cfg,
                "constraint_soft_bathroom_location_preference",
                CONSTRAINT_SOFT_BATHROOM_LOCATION_PREFERENCE,
            )
        )
        self.constraint_soft_layout_dead_space_penalty = bool(
            getattr(cfg, "constraint_soft_layout_dead_space_penalty", CONSTRAINT_SOFT_LAYOUT_DEAD_SPACE_PENALTY)
        )
        self.constraint_soft_seed_facade_depth_penalty = bool(
            getattr(
                cfg,
                "constraint_soft_seed_facade_depth_penalty",
                CONSTRAINT_SOFT_SEED_FACADE_DEPTH_PENALTY,
            )
        )
        self.constraint_soft_seed_facade_alignment_penalty = bool(
            getattr(
                cfg,
                "constraint_soft_seed_facade_alignment_penalty",
                CONSTRAINT_SOFT_SEED_FACADE_ALIGNMENT_PENALTY,
            )
        )
        self.constraint_soft_recessed_facade_penalty = bool(
            getattr(cfg, "constraint_soft_recessed_facade_penalty", CONSTRAINT_SOFT_RECESSED_FACADE_PENALTY)
        )

        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.last_status: int | None = None
        self.last_status_name: str = "NOT_RUN"

        self.rooms: list[Room] = [
            Room(r.name, r.min_w, r.min_h, r.max_w, r.max_h, r.type)
            for r in self.requirements.rooms
        ]

        living_room = generate_living_room(self.requirements)
        hallway_rooms = generate_hallway_rooms(self.requirements)
        system_added_rooms = [living_room] + hallway_rooms
        self.mandatory_relations: list[RoomRelationsConstraint] = []

        existing_types = {r.type for r in self.rooms}
        existing_names = {r.name for r in self.rooms}
        for room in system_added_rooms:
            if room.type == "livingRoom":
                if room.type not in existing_types:
                    self.rooms.append(room)
                    existing_types.add(room.type)
            elif room.name not in existing_names:
                self.rooms.append(room)
                existing_names.add(room.name)

    def solve(
        self,
        seed_layout: list[dict[str, Any]] | None = None,
        wiggle_room: int = 0,
        include_constraint_b_soft: bool = False,
        include_constraint_a_soft: bool = False,
        include_constraint_c_soft: bool = False,
        include_constraint_d_soft: bool = False,
        max_time_seconds: float = DEFAULT_SOLVER_MAX_TIME_SECONDS,
        debug_log: bool = False,
    ) -> bool:
        w_int = int(self.floor_plan_width)
        h_int = int(self.floor_plan_height)

        for room in self.rooms:
            room.create_variables(self.model, w_int, h_int)

        if debug_log:
            self.print_dev_log()

        if self.constraint_hard_basic_geometry:
            add_basic_constraints(self.model, self.rooms)

        if self.constraint_hard_hallway_rules and self.hallway_count > 0:
            add_hallway_constraints(self.model, self.rooms)

        if self.constraint_hard_room_shared_walls:
            add_room_shared_wall_constraints(self.model, self.rooms)

        soft_relation_constraints: list[RoomRelationsConstraint] = []
        hard_or_relation_constraints: list[RoomRelationsConstraint] = []
        hard_and_relation_constraints: list[RoomRelationsConstraint] = []

        for relation in self.relation_constraints:
            relation_obj = RoomRelationsConstraint.model_validate(relation)
            level = str(getattr(relation_obj, "constraint_level", "soft") or "soft").strip().lower()
            if level == "hard_and":
                hard_and_relation_constraints.append(relation_obj)
            elif level == "hard_or":
                hard_or_relation_constraints.append(relation_obj)
            else:
                soft_relation_constraints.append(relation_obj)

        hard_and_relation_constraints = self.mandatory_relations + hard_and_relation_constraints

        if self.constraint_hard_room_adjacency:
            apply_hard_room_adjacency_constraints(
                self.model,
                self.rooms,
                hard_and_relations=hard_and_relation_constraints,
                hard_or_relations=hard_or_relation_constraints,
                min_overlap=GENERATOR_ADJACENCY_MIN_OVERLAP,
            )

        if self.constraint_soft_room_adjacency_preference:
            build_soft_room_adjacency_preference_vars(
                self.model,
                self.rooms,
                soft_relations=soft_relation_constraints,
                min_overlap=GENERATOR_ADJACENCY_MIN_OVERLAP,
            )

        if self.constraint_hard_minimum_area_coverage:
            add_minimum_area_coverage(
                self.model,
                self.rooms,
                self.floor_plan_width,
                self.floor_plan_height,
                self.min_coverage,
            )

        if self.constraint_hard_room_size_hierarchy:
            add_room_size_hierarchy(self.model, self.rooms)

        if self.constraint_hard_living_room_location:
            add_living_room_bottom_most_constraint(self.model, self.rooms)

        if self.constraint_hard_envelope_staircase and self.envelope_enabled:
            add_envelope_staircase_constraints(
                self.model,
                self.rooms,
                floor_width=w_int,
                floor_height=h_int,
                min_gap=self.envelope_min_gap,
                max_gap=self.envelope_max_gap,
                exclude_types=self.envelope_exclude_types,
                apply_sides=self.envelope_apply_sides,
            )

        seed_context = None
        if seed_layout:
            seed_context = build_seed_layout_context(seed_layout)
            if self.constraint_soft_seed_layout_hints:
                apply_seed_layout_hints_with_wiggle(
                    self.model,
                    self.rooms,
                    seed_layout,
                    self.floor_plan_width,
                    self.floor_plan_height,
                    wiggle_room=wiggle_room,
                )

        objective_terms: list[cp_model.LinearExprT] = []

        if self.constraint_soft_compact_layout_center_proximity:
            objective_terms.append(
                add_center_proximity_objective(
                    self.model,
                    self.rooms,
                    self.floor_plan_width,
                    self.floor_plan_height,
                )
            )

        if self.constraint_soft_bathroom_location_preference:
            objective_terms.append(
                build_bathroom_location_preference_penalty(
                    self.model,
                    self.rooms,
                    self.floor_plan_height,
                    bathroom_weight=BATHROOM_LOCATION_WEIGHT,
                )
            )

        if self.constraint_soft_layout_dead_space_penalty and include_constraint_a_soft:
            objective_terms.append(
                build_layout_dead_space_penalty(
                    self.model,
                    self.rooms,
                    self.floor_plan_width,
                    self.floor_plan_height,
                    dead_space_weight=SOFT_LAYOUT_DEAD_SPACE_WEIGHT,
                )
            )

        if (
            self.constraint_soft_seed_facade_depth_penalty
            and include_constraint_b_soft
            and seed_context is not None
        ):
            objective_terms.append(
                build_seed_facade_depth_penalty(
                    self.model,
                    self.rooms,
                    seed_context,
                    self.floor_plan_width,
                    self.floor_plan_height,
                    depth_weight=SOFT_SEED_FACADE_DEPTH_WEIGHT,
                )
            )

        if (
            self.constraint_soft_seed_facade_alignment_penalty
            and include_constraint_c_soft
            and seed_context is not None
        ):
            objective_terms.append(
                build_seed_facade_alignment_penalty(
                    self.model,
                    self.rooms,
                    seed_context,
                    self.floor_plan_width,
                    self.floor_plan_height,
                    align_weight=SOFT_SEED_FACADE_ALIGNMENT_WEIGHT,
                    align_threshold=SOFT_SEED_FACADE_ALIGNMENT_THRESHOLD,
                )
            )

        if (
            self.constraint_soft_recessed_facade_penalty
            and include_constraint_d_soft
            and seed_context is not None
        ):
            objective_terms.append(
                build_recessed_facade_penalty(
                    self.model,
                    self.rooms,
                    seed_context,
                    self.floor_plan_width,
                    self.floor_plan_height,
                    near_band=SOFT_RECESSED_FACADE_NEAR_BAND,
                    base_threshold=SOFT_RECESSED_FACADE_BASE_THRESHOLD,
                    severe_threshold=SOFT_RECESSED_FACADE_SEVERE_THRESHOLD,
                    base_weight=SOFT_RECESSED_FACADE_BASE_WEIGHT,
                    severe_weight=SOFT_RECESSED_FACADE_SEVERE_WEIGHT,
                    attach_weight=SOFT_RECESSED_FACADE_ATTACH_WEIGHT,
                    side_gap_threshold=SOFT_RECESSED_FACADE_SIDE_GAP_THRESHOLD,
                )
            )

        if objective_terms:
            total_cost = cp_model.LinearExpr.Sum(objective_terms)  # type: ignore
            self.model.Minimize(total_cost)

        self.solver.parameters.max_time_in_seconds = max(0.1, float(max_time_seconds))
        self.solver.parameters.random_seed = random.randint(0, 1000)
        self.solver.parameters.randomize_search = True

        status = self.solver.Solve(self.model)
        self.last_status = status
        self.last_status_name = self.solver.StatusName(status)
        return status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

    def get_solution(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for room in self.rooms:
            assert (
                room.x is not None
                and room.y is not None
                and room.w is not None
                and room.h is not None
                and room.x_end is not None
                and room.y_end is not None
                and room.area is not None
            ), f"Room variables not initialized for {room.name}"

            results.append(
                {
                    "name": room.name,
                    "type": room.type,
                    "x": self.solver.Value(room.x),
                    "y": self.solver.Value(room.y),
                    "w": self.solver.Value(room.w),
                    "h": self.solver.Value(room.h),
                    "x_end": self.solver.Value(room.x_end),
                    "y_end": self.solver.Value(room.y_end),
                    "area": self.solver.Value(room.area),
                }
            )
        return results

    def print_dev_log(self) -> None:
        print("\n" + "=" * 100)
        print("FLOOR PLAN GENERATOR - PRE-CONSTRAINT LOG")
        print("=" * 100)
        print(f"\nFloor Dimensions: {self.floor_plan_width} x {self.floor_plan_height}")
        print(f"Minimum Coverage Requirement: {self.min_coverage * 100:.1f}%")
        print(f"\nTotal Rooms to be Constrained: {len(self.rooms)}")
        print("\n" + "-" * 100)

        for i, room in enumerate(self.rooms, 1):
            print(f"\n[Room {i}] {room.name}")
            print(f"  Type:                {room.type}")
            print(f"  Width Bounds:        {room.min_w} - {room.max_w} units")
            print(f"  Height Bounds:       {room.min_h} - {room.max_h} units")
            print(f"  Min Possible Area:   {room.min_w * room.min_h} units")
            print(f"  Max Possible Area:   {room.max_w * room.max_h} units")

        print("\n" + "=" * 100)
        print("[Status] Room variables created. Constraints about to be applied...")
        print("=" * 100 + "\n")

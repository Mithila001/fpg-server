from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from ortools.sat.python import cp_model

from app.core.fpg_rooms.config_fpg import (
    BATHROOM_LOCATION_WEIGHT,
    DEFAULT_SOLVER_MAX_TIME_SECONDS,
    ENVELOPE_APPLY_SIDES,
    ENVELOPE_ENABLED,
    ENVELOPE_EXCLUDE_TYPES,
    ENVELOPE_MAX_GAP,
    ENVELOPE_MIN_GAP,
    GENERATOR_ADJACENCY_MIN_OVERLAP,
)

from .constraints.adjacency_constraints import adjacency_constraints
from .constraints.basic_constraints import add_basic_constraints
from .constraints.compact_layout import add_center_proximity_objective
from .constraints.envelope_staircase import add_envelope_staircase_constraints
from .constraints.floor_area_coverage import add_minimum_area_coverage
from .constraints.hallway_constraints import add_hallway_constraints
from .constraints.room_location import room_location_hard, room_location_soft
from .constraints.room_shared_wall_constraints import add_room_shared_wall_constraints
from .constraints.room_size_hierarchy_constraints import add_room_size_hierarchy
from .rules import normalize_requirements
from .solver_models.room import Room
from .types.room import FpgRequirements
from .types.room_relations_constraints import RoomRelationsConstraint
from .utils.generator.util_hallway_rooms import (
    generate_hallway_rooms,
    prepare_requirements_for_hallway_rules,
)
from .utils.generator.util_living_room import generate_living_room


@dataclass(frozen=True)
class ConstraintBStats:
    front_facing_room_count: int
    back_facing_room_count: int
    left_facing_room_count: int
    right_facing_room_count: int


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

        add_basic_constraints(self.model, self.rooms)

        if self.hallway_count > 0:
            add_hallway_constraints(self.model, self.rooms)

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

        adjacency_constraints(
            self.model,
            self.rooms,
            hard_AND_Relations=hard_and_relation_constraints,
            hard_OR_Relations=hard_or_relation_constraints,
            softRelations=soft_relation_constraints,
            min_overlap=GENERATOR_ADJACENCY_MIN_OVERLAP,
        )

        add_minimum_area_coverage(
            self.model,
            self.rooms,
            self.floor_plan_width,
            self.floor_plan_height,
            self.min_coverage,
        )
        add_room_size_hierarchy(self.model, self.rooms)
        room_location_hard(self.model, self.rooms)

        if self.envelope_enabled:
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

        if seed_layout:
            self._apply_seed_hints_and_wiggle(seed_layout, wiggle_room)

        center_cost = add_center_proximity_objective(
            self.model,
            self.rooms,
            self.floor_plan_width,
            self.floor_plan_height,
        )
        bathroom_location_cost = room_location_soft(
            self.model,
            self.rooms,
            self.floor_plan_height,
            bathroom_weight=BATHROOM_LOCATION_WEIGHT,
        )

        objective_terms: list[cp_model.LinearExprT] = [center_cost, bathroom_location_cost]
        if include_constraint_b_soft and seed_layout:
            objective_terms.append(self._constraint_b_soft_penalty(seed_layout))
        if include_constraint_a_soft:
            objective_terms.append(self._constraint_a_soft_penalty())
        if include_constraint_d_soft and seed_layout:
            objective_terms.append(self._constraint_d_soft_penalty(seed_layout))

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

    def _apply_seed_hints_and_wiggle(self, seed_layout: list[dict[str, Any]], wiggle_room: int) -> None:
        seed_by_name = {
            str(r.get("name")): r
            for r in seed_layout
            if isinstance(r, dict) and r.get("name") is not None
        }

        w_int = int(self.floor_plan_width)
        h_int = int(self.floor_plan_height)
        wiggle = max(0, int(wiggle_room))

        for room in self.rooms:
            seed = seed_by_name.get(room.name)
            if seed is None:
                continue

            assert room.x is not None and room.y is not None
            assert room.w is not None and room.h is not None
            assert room.x_end is not None and room.y_end is not None

            sx = int(seed.get("x", 0))
            sy = int(seed.get("y", 0))

            # Quick post-process payloads may omit w/h; derive from endpoints.
            seed_w_raw = seed.get("w")
            seed_h_raw = seed.get("h")
            if seed_w_raw is None:
                seed_x_end = int(seed.get("x_end", sx + room.min_w))
                seed_w_raw = seed_x_end - sx
            if seed_h_raw is None:
                seed_y_end = int(seed.get("y_end", sy + room.min_h))
                seed_h_raw = seed_y_end - sy

            sw = int(seed_w_raw)
            sh = int(seed_h_raw)
            sw = max(room.min_w, min(room.max_w, sw))
            sh = max(room.min_h, min(room.max_h, sh))

            self.model.AddHint(room.x, sx)
            self.model.AddHint(room.y, sy)
            self.model.AddHint(room.w, sw)
            self.model.AddHint(room.h, sh)

            if wiggle <= 0:
                continue

            x_lb = max(0, sx - wiggle)
            y_lb = max(0, sy - wiggle)
            w_lb = max(room.min_w, sw - wiggle)
            h_lb = max(room.min_h, sh - wiggle)

            x_ub = min(w_int - room.min_w, sx + wiggle)
            y_ub = min(h_int - room.min_h, sy + wiggle)
            w_ub = min(room.max_w, sw + wiggle)
            h_ub = min(room.max_h, sh + wiggle)

            self.model.Add(room.x >= min(x_lb, x_ub))  # type: ignore
            self.model.Add(room.x <= max(x_lb, x_ub))  # type: ignore
            self.model.Add(room.y >= min(y_lb, y_ub))  # type: ignore
            self.model.Add(room.y <= max(y_lb, y_ub))  # type: ignore

            self.model.Add(room.w >= min(w_lb, w_ub))  # type: ignore
            self.model.Add(room.w <= max(w_lb, w_ub))  # type: ignore
            self.model.Add(room.h >= min(h_lb, h_ub))  # type: ignore
            self.model.Add(room.h <= max(h_lb, h_ub))  # type: ignore

    def _constraint_b_soft_penalty(self, seed_layout: list[dict[str, Any]]) -> cp_model.LinearExprT:
        seed_by_name = {
            str(r.get("name")): r
            for r in seed_layout
            if isinstance(r, dict) and r.get("name") is not None
        }
        if not seed_by_name:
            return 0

        seed_rooms = list(seed_by_name.values())
        left_line = min(int(r.get("x", 0)) for r in seed_rooms)
        right_line = max(int(r.get("x_end", r.get("x", 0))) for r in seed_rooms)
        back_line = min(int(r.get("y", 0)) for r in seed_rooms)
        front_line = max(int(r.get("y_end", r.get("y", 0))) for r in seed_rooms)

        front_facing = [r for r in seed_rooms if int(r.get("y_end", 0)) == front_line]
        back_facing = [r for r in seed_rooms if int(r.get("y", 0)) == back_line]
        left_facing = [r for r in seed_rooms if int(r.get("x", 0)) == left_line]
        right_facing = [r for r in seed_rooms if int(r.get("x_end", 0)) == right_line]

        side_facing_names = {
            "front": {str(r.get("name")) for r in front_facing},
            "back": {str(r.get("name")) for r in back_facing},
            "left": {str(r.get("name")) for r in left_facing},
            "right": {str(r.get("name")) for r in right_facing},
        }

        terms: list[cp_model.IntVar] = []
        side_recessed: dict[str, list[cp_model.IntVar]] = {
            "front": [],
            "back": [],
            "left": [],
            "right": [],
        }

        for room in self.rooms:
            assert room.x is not None and room.y is not None
            assert room.x_end is not None and room.y_end is not None

            if room.name in side_facing_names["front"]:
                penalty, recessed = self._side_depth_penalty(
                    depth_expr=front_line - room.y_end,
                    name=f"b_front_{room.name}",
                    max_depth=max(1, int(self.floor_plan_height)),
                )
                terms.append(penalty)
                side_recessed["front"].append(recessed)

            if room.name in side_facing_names["back"]:
                penalty, recessed = self._side_depth_penalty(
                    depth_expr=room.y - back_line,
                    name=f"b_back_{room.name}",
                    max_depth=max(1, int(self.floor_plan_height)),
                )
                terms.append(penalty)
                side_recessed["back"].append(recessed)

            if room.name in side_facing_names["left"]:
                penalty, recessed = self._side_depth_penalty(
                    depth_expr=room.x - left_line,
                    name=f"b_left_{room.name}",
                    max_depth=max(1, int(self.floor_plan_width)),
                )
                terms.append(penalty)
                side_recessed["left"].append(recessed)

            if room.name in side_facing_names["right"]:
                penalty, recessed = self._side_depth_penalty(
                    depth_expr=right_line - room.x_end,
                    name=f"b_right_{room.name}",
                    max_depth=max(1, int(self.floor_plan_width)),
                )
                terms.append(penalty)
                side_recessed["right"].append(recessed)

        # Count soft limits for stepped facade structures.
        terms.append(
            self._excess_count_penalty(
                vars_to_count=side_recessed["front"],
                max_allowed=0 if len(front_facing) < 1 else 2,
                name="b_front_count",
            )
        )
        combined_lr = side_recessed["left"] + side_recessed["right"]
        terms.append(
            self._excess_count_penalty(
                vars_to_count=combined_lr,
                max_allowed=0 if (len(left_facing) + len(right_facing)) < 2 else 1,
                name="b_left_right_count",
            )
        )
        terms.append(
            self._excess_count_penalty(
                vars_to_count=side_recessed["back"],
                max_allowed=0 if len(back_facing) < 1 else 1,
                name="b_back_count",
            )
        )

        weighted_terms: list[cp_model.LinearExprT] = []
        for term in terms:
            weighted_terms.append(term * 25)

        return cp_model.LinearExpr.Sum(weighted_terms)  # type: ignore

    def _constraint_a_soft_penalty(self) -> cp_model.LinearExprT:
        """Constraint A: minimize dead space inside the current layout envelope."""
        if not self.rooms:
            return 0

        x_vars = []
        y_vars = []
        x_end_vars = []
        y_end_vars = []
        area_vars = []

        for room in self.rooms:
            assert room.x is not None and room.y is not None
            assert room.x_end is not None and room.y_end is not None
            assert room.area is not None
            x_vars.append(room.x)
            y_vars.append(room.y)
            x_end_vars.append(room.x_end)
            y_end_vars.append(room.y_end)
            area_vars.append(room.area)

        w_int = int(self.floor_plan_width)
        h_int = int(self.floor_plan_height)

        left_edge = self.model.NewIntVar(0, w_int, "a_bbox_left")  # type: ignore
        right_edge = self.model.NewIntVar(0, w_int, "a_bbox_right")  # type: ignore
        bottom_edge = self.model.NewIntVar(0, h_int, "a_bbox_bottom")  # type: ignore
        top_edge = self.model.NewIntVar(0, h_int, "a_bbox_top")  # type: ignore

        self.model.AddMinEquality(left_edge, x_vars)  # type: ignore
        self.model.AddMaxEquality(right_edge, x_end_vars)  # type: ignore
        self.model.AddMinEquality(bottom_edge, y_vars)  # type: ignore
        self.model.AddMaxEquality(top_edge, y_end_vars)  # type: ignore

        bbox_w = self.model.NewIntVar(0, w_int, "a_bbox_w")  # type: ignore
        bbox_h = self.model.NewIntVar(0, h_int, "a_bbox_h")  # type: ignore
        self.model.Add(bbox_w == right_edge - left_edge)  # type: ignore
        self.model.Add(bbox_h == top_edge - bottom_edge)  # type: ignore

        bbox_area = self.model.NewIntVar(0, w_int * h_int, "a_bbox_area")  # type: ignore
        self.model.AddMultiplicationEquality(bbox_area, [bbox_w, bbox_h])  # type: ignore

        rooms_area_sum = self.model.NewIntVar(0, w_int * h_int, "a_rooms_area_sum")  # type: ignore
        self.model.Add(rooms_area_sum == cp_model.LinearExpr.Sum(area_vars))  # type: ignore

        dead_space = self.model.NewIntVar(0, w_int * h_int, "a_dead_space")  # type: ignore
        self.model.Add(dead_space == bbox_area - rooms_area_sum)  # type: ignore
        return dead_space * 12

    def _constraint_d_soft_penalty(self, seed_layout: list[dict[str, Any]]) -> cp_model.LinearExprT:
        """Constraint D: penalize facade recess depths above 10 for near-facade rooms."""
        seed_by_name = {
            str(r.get("name")): r
            for r in seed_layout
            if isinstance(r, dict) and r.get("name") is not None
        }
        if not seed_by_name:
            return 0

        seed_rooms = list(seed_by_name.values())
        left_line = min(int(r.get("x", 0)) for r in seed_rooms)
        right_line = max(int(r.get("x_end", r.get("x", 0))) for r in seed_rooms)
        back_line = min(int(r.get("y", 0)) for r in seed_rooms)
        front_line = max(int(r.get("y_end", r.get("y", 0))) for r in seed_rooms)

        side_near_names: dict[str, set[str]] = {
            "front": set(),
            "back": set(),
            "left": set(),
            "right": set(),
        }

        near_band = 20
        for room in seed_rooms:
            name = str(room.get("name"))
            sx = int(room.get("x", 0))
            sy = int(room.get("y", 0))
            sx_end = int(room.get("x_end", sx))
            sy_end = int(room.get("y_end", sy))

            if front_line - sy_end <= near_band:
                side_near_names["front"].add(name)
            if sy - back_line <= near_band:
                side_near_names["back"].add(name)
            if sx - left_line <= near_band:
                side_near_names["left"].add(name)
            if right_line - sx_end <= near_band:
                side_near_names["right"].add(name)

        terms: list[cp_model.IntVar] = []
        max_w = max(1, int(self.floor_plan_width))
        max_h = max(1, int(self.floor_plan_height))

        for room in self.rooms:
            assert room.x is not None and room.y is not None
            assert room.x_end is not None and room.y_end is not None

            if room.name in side_near_names["front"]:
                terms.append(
                    self._excess_depth_penalty(
                        depth_expr=front_line - room.y_end,
                        threshold=10,
                        max_depth=max_h,
                        name=f"d_front_{room.name}",
                    )
                )

            if room.name in side_near_names["back"]:
                terms.append(
                    self._excess_depth_penalty(
                        depth_expr=room.y - back_line,
                        threshold=10,
                        max_depth=max_h,
                        name=f"d_back_{room.name}",
                    )
                )

            if room.name in side_near_names["left"]:
                terms.append(
                    self._excess_depth_penalty(
                        depth_expr=room.x - left_line,
                        threshold=10,
                        max_depth=max_w,
                        name=f"d_left_{room.name}",
                    )
                )

            if room.name in side_near_names["right"]:
                terms.append(
                    self._excess_depth_penalty(
                        depth_expr=right_line - room.x_end,
                        threshold=10,
                        max_depth=max_w,
                        name=f"d_right_{room.name}",
                    )
                )

        if not terms:
            return 0

        weighted_terms: list[cp_model.LinearExprT] = [term * 20 for term in terms]
        return cp_model.LinearExpr.Sum(weighted_terms)  # type: ignore

    def _excess_depth_penalty(
        self,
        depth_expr: cp_model.LinearExprT,
        threshold: int,
        max_depth: int,
        name: str,
    ) -> cp_model.IntVar:
        depth = self.model.NewIntVar(-max_depth, max_depth, f"{name}_depth")  # type: ignore
        self.model.Add(depth == depth_expr)

        depth_pos = self.model.NewIntVar(0, max_depth, f"{name}_depth_pos")  # type: ignore
        self.model.AddMaxEquality(depth_pos, [depth, 0])  # type: ignore

        raw_excess = self.model.NewIntVar(-max_depth, max_depth, f"{name}_raw_excess")  # type: ignore
        self.model.Add(raw_excess == depth_pos - threshold)

        excess = self.model.NewIntVar(0, max_depth, f"{name}_excess")  # type: ignore
        self.model.AddMaxEquality(excess, [raw_excess, 0])  # type: ignore
        return excess

    def _side_depth_penalty(
        self,
        depth_expr: cp_model.LinearExprT,
        name: str,
        max_depth: int,
    ) -> tuple[cp_model.IntVar, cp_model.IntVar]:
        depth = self.model.NewIntVar(-max_depth, max_depth, f"{name}_depth")  # type: ignore
        self.model.Add(depth == depth_expr)

        depth_pos = self.model.NewIntVar(0, max_depth, f"{name}_depth_pos")  # type: ignore
        self.model.AddMaxEquality(depth_pos, [depth, 0])  # type: ignore

        recessed = self.model.NewBoolVar(f"{name}_recessed")  # type: ignore
        self.model.Add(depth_pos >= 1).OnlyEnforceIf(recessed)
        self.model.Add(depth_pos == 0).OnlyEnforceIf(recessed.Not())

        too_large_raw = self.model.NewIntVar(-max_depth, max_depth, f"{name}_too_large_raw")  # type: ignore
        self.model.Add(too_large_raw == depth_pos - 20)
        too_large = self.model.NewIntVar(0, max_depth, f"{name}_too_large")  # type: ignore
        self.model.AddMaxEquality(too_large, [too_large_raw, 0])  # type: ignore

        small_raw = self.model.NewIntVar(-max_depth, max_depth, f"{name}_small_raw")  # type: ignore
        self.model.Add(small_raw == 5 - depth_pos)
        small_gap = self.model.NewIntVar(0, max_depth, f"{name}_small_gap")  # type: ignore
        self.model.AddMaxEquality(small_gap, [small_raw, 0])  # type: ignore

        too_small = self.model.NewIntVar(0, max_depth, f"{name}_too_small")  # type: ignore
        self.model.Add(too_small == small_gap).OnlyEnforceIf(recessed)
        self.model.Add(too_small == 0).OnlyEnforceIf(recessed.Not())

        penalty = self.model.NewIntVar(0, max_depth * 2, f"{name}_penalty")  # type: ignore
        self.model.Add(penalty == too_small + too_large)
        return penalty, recessed

    def _excess_count_penalty(
        self,
        vars_to_count: list[cp_model.IntVar],
        max_allowed: int,
        name: str,
    ) -> cp_model.IntVar:
        if not vars_to_count:
            penalty = self.model.NewIntVar(0, 0, f"{name}_penalty")  # type: ignore
            self.model.Add(penalty == 0)
            return penalty

        count_var = self.model.NewIntVar(0, len(vars_to_count), f"{name}_count")  # type: ignore
        self.model.Add(count_var == cp_model.LinearExpr.Sum(vars_to_count))  # type: ignore

        raw_excess = self.model.NewIntVar(-len(vars_to_count), len(vars_to_count), f"{name}_raw_excess")  # type: ignore
        self.model.Add(raw_excess == count_var - max_allowed)

        excess = self.model.NewIntVar(0, len(vars_to_count), f"{name}_excess")  # type: ignore
        self.model.AddMaxEquality(excess, [raw_excess, 0])  # type: ignore
        return excess

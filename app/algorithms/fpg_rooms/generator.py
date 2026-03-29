from ortools.sat.python import cp_model
import random
from .solver_models.room import Room
from .types.room import FpgRequirements
from .rules import normalize_requirements
from .utils.generator.util_hallway_rooms import (
    generate_hallway_rooms,
    prepare_requirements_for_hallway_rules,
)
from .utils.generator.util_living_room import generate_living_room
from .constraints.basic_constraints import add_basic_constraints
from .constraints.adjacency_constraints import adjacency_constraints
from .types.room_relations_constraints import RoomRelationsConstraint
from .constraints.floor_area_coverage import add_minimum_area_coverage
from .constraints.room_size_hierarchy_constraints import add_room_size_hierarchy
from .constraints.compact_layout import add_center_proximity_objective
from .constraints.hallway_constraints import add_hallway_constraints
from .constraints.room_shared_wall_constraints import add_room_shared_wall_constraints
from .constraints.room_location import room_location_hard, room_location_soft
from .constraints.envelope_staircase import add_envelope_staircase_constraints
from app.core.fpg_rooms.config_fpg import (
    ENVELOPE_ENABLED,
    ENVELOPE_MIN_GAP,
    ENVELOPE_MAX_GAP,
    ENVELOPE_EXCLUDE_TYPES,
    ENVELOPE_APPLY_SIDES,
    GENERATOR_ADJACENCY_MIN_OVERLAP,
    BATHROOM_LOCATION_WEIGHT,
    DEFAULT_SOLVER_MAX_TIME_SECONDS,
)


class FloorPlanGenerator:
    def __init__(self, requirements: FpgRequirements):
        """Initialize generator from a full requirements object.

        ``requirements`` bundles room specifications and configuration
        parameters (coverage, aspect ratios, floor size, etc.) and relation constraints.

        We first normalize the incoming data with ``rules.normalize_requirements``
        so that downstream code can rely on sensible numeric values.
        """
        requirements = normalize_requirements(requirements)
        requirements = prepare_requirements_for_hallway_rules(requirements)
        self.requirements = requirements

        # Store relation constraints from the updated requirements object.
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

        # Initializing Rooms
        self.rooms: list[Room] = [
            Room(r.name, r.min_w, r.min_h, r.max_w, r.max_h, r.type)
            for r in self.requirements.rooms
        ]

        # Add mandatory rooms (living room + hallway) from code, not user input.
        # Avoid duplicates if upstream payload already includes those types.
        living_room = generate_living_room(self.requirements)
        hallway_rooms = generate_hallway_rooms(self.requirements)
        system_added_rooms = [living_room] + hallway_rooms
        self.mandatory_relations = []

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

    def generate(self) -> bool:
        """Build and solve the floor plan. Returns True if a solution was found."""
        # OR-Tools only accepts integer bounds, so cast the float dimensions.
        w_int = int(self.floor_plan_width)
        h_int = int(self.floor_plan_height)
        for room in self.rooms:
            room.create_variables(self.model, w_int, h_int)

        # Print debug log before applying constraints
        self.printDevLog()

        add_basic_constraints(self.model, self.rooms)

        if self.hallway_count > 0:
            add_hallway_constraints(self.model, self.rooms)

        add_room_shared_wall_constraints(self.model, self.rooms)

        # Use relation constraints from requirements (passed from algorithm_manager)
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

        # Use fixed adjacency overlap requirement (at least 1 unit of shared edge).
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

        # Soft objective: cluster rooms toward the center via Manhattan distance.
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
        total_cost = cp_model.LinearExpr.Sum([center_cost, bathroom_location_cost])  # type: ignore

        self.model.Minimize(total_cost)

        self.solver.parameters.max_time_in_seconds = DEFAULT_SOLVER_MAX_TIME_SECONDS
        self.solver.parameters.random_seed = random.randint(0, 1000)
        self.solver.parameters.randomize_search = True
        status = self.solver.Solve(self.model)
        self.last_status = status
        self.last_status_name = self.solver.StatusName(status)

        return status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

    def get_solution(self) -> list[dict]:
        """Extract room placements from the solver after a successful solve."""
        results = []
        for room in self.rooms:
            # Variable creation happens in generate(); assert for type narrowing.
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

    def printDevLog(self) -> None:
        """=== Print room information and configuration before constraints are applied. ==="""
        print("\n" + "="*100)
        print("FLOOR PLAN GENERATOR - PRE-CONSTRAINT LOG")
        print("="*100)
        print(f"\nFloor Dimensions: {self.floor_plan_width} x {self.floor_plan_height}")
        print(f"Minimum Coverage Requirement: {self.min_coverage * 100:.1f}%")
        print(f"\nTotal Rooms to be Constrained: {len(self.rooms)}")
        print("\n" + "-"*100)

        for i, room in enumerate(self.rooms, 1):
            print(f"\n[Room {i}] {room.name}")
            print(f"  Type:                {room.type}")
            print(f"  Width Bounds:        {room.min_w} - {room.max_w} units")
            print(f"  Height Bounds:       {room.min_h} - {room.max_h} units")
            print(f"  Min Possible Area:   {room.min_w * room.min_h} units")
            print(f"  Max Possible Area:   {room.max_w * room.max_h} units")
            if room.x is not None:
                print("  CP Variables:        x, y, w, h, x_end, y_end, area (created)")

        print("\n" + "="*100)
        print("[Status] Room variables created. Constraints about to be applied...")
        print("="*100 + "\n")

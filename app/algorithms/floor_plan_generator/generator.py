from ortools.sat.python import cp_model
import random
from typing import List, Tuple
from .solver_models.room import Room
from .types.room import FpgRequirements
from .rules import normalize_requirements
from .constraints.basic_constraints import add_basic_constraints
from .constraints.adjacency_constraints import adjacency_constraints
from app.schemas.db.room_relations_constraints import RoomRelationsConstraintBase
from .constraints.floor_area_coverage import add_minimum_area_coverage
from .constraints.room_size_hierarchy_constraints import add_room_size_hierarchy
from .constraints.compact_layout import add_center_proximity_objective
from .constraints.hallway_constraints import add_hallway_constraints


def add_mandatory_data(
    floor_width: float,
    floor_height: float,
) -> Tuple[List[Room], List[RoomRelationsConstraintBase]]:
    """Create mandatory rooms and their hardcoded relation rules.

    Returns:
        Tuple of (mandatory_rooms, mandatory_relations)
        - mandatory_rooms: List of Room objects (living room, hallway(s))
        - mandatory_relations: List of pre-defined RoomRelationsConstraintBase
          defining rules for mandatory rooms (e.g., hallway must touch living room)

    These are system-mandatory and not configurable via database input.
    They are merged with user-provided database relations during generation.
    """
    # Keep bounds permissive so mandatory rooms can coexist on small floors.
    living_room = Room(
        "Living Room",
        0,
        0,
        int(floor_width),
        int(floor_height),
        "livingRoom",
    )

    # Hallway size is restricted later by hallway constraints.
    hallway_room = Room(
        "Hallway",
        0,
        0,
        int(floor_width),
        int(floor_height),
        "hallway",
    )

    mandatory_rooms = [living_room, hallway_room]

    # Relation list is intentionally empty; hallway/living linkage is enforced
    # by hallway constraints in the solver phase.
    mandatory_relations = []

    return mandatory_rooms, mandatory_relations


class FloorPlanGenerator:
    def __init__(self, requirements: FpgRequirements):
        """Initialize generator from a full requirements object.

        ``requirements`` bundles room specifications and configuration
        parameters (coverage, aspect ratios, floor size, etc.) and relation constraints.

        We first normalize the incoming data with ``rules.normalize_requirements``
        so that downstream code can rely on sensible numeric values.
        """
        # Store relation constraints from requirements before normalization
        self.relation_constraints_raw = requirements.relation_constraints
        
        requirements = normalize_requirements(requirements)

        cfg = requirements.config
        self.floor_plan_width: float = cfg.floor_plan_width
        self.floor_plan_height: float = cfg.floor_plan_height
        self.min_coverage: float = cfg.min_coverage

        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()

        # Initializing Rooms
        self.rooms: list[Room] = [
            Room(r.name, r.min_w, r.min_h, r.max_w, r.max_h, r.type)
            for r in requirements.rooms
        ]

        # Add mandatory rooms (living room + hallway) from code, not user input.
        # Avoid duplicates if upstream payload already includes those types.
        mandatory_rooms, self.mandatory_relations = add_mandatory_data(
            self.floor_plan_width, self.floor_plan_height
        )
        existing_types = {r.type for r in self.rooms}
        for room in mandatory_rooms:
            if room.type not in existing_types:
                self.rooms.append(room)
                existing_types.add(room.type)

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

        add_hallway_constraints(self.model, self.rooms)

        # Use relation constraints from requirements (passed from algorithm_manager)
        relations_schema = [
            RoomRelationsConstraintBase.model_validate(r) for r in self.relation_constraints_raw
        ]  # type: ignore[assignment]

        all_relations = self.mandatory_relations + relations_schema

        adjacency_constraints(
            self.model,
            self.rooms,
            hardRelations=all_relations,
            softRelations=all_relations,
        )

        add_minimum_area_coverage(
            self.model,
            self.rooms,
            self.floor_plan_width,
            self.floor_plan_height,
            self.min_coverage,
        )
        add_room_size_hierarchy(self.model, self.rooms)

        # Soft objective: cluster rooms toward the center via Manhattan distance.
        cost = add_center_proximity_objective(
            self.model,
            self.rooms,
            self.floor_plan_width,
            self.floor_plan_height,
        )

        self.model.Minimize(cost)

        self.solver.parameters.max_time_in_seconds = 1.0
        self.solver.parameters.random_seed = random.randint(0, 1000)
        self.solver.parameters.randomize_search = True
        status = self.solver.Solve(self.model)

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
        """Print room information and configuration before constraints are applied."""
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
            print(f"  Min Possible Area:   {room.min_w * room.min_h} sq units")
            print(f"  Max Possible Area:   {room.max_w * room.max_h} sq units")
            if room.x is not None:
                print("  CP Variables:        x, y, w, h, x_end, y_end, area (created)")

        print("\n" + "="*100)
        print("[Status] Room variables created. Constraints about to be applied...")
        print("="*100 + "\n")

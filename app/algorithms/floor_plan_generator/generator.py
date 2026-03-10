from ortools.sat.python import cp_model
import random
from .solver_models.room import Room
from .types.room import FpgRequirements
from .rules import normalize_requirements
from .constraints.basic_constraints import add_basic_constraints
from .constraints.adjacency_constraints import add_kitchen_living_adjacency
from .constraints.floor_area_coverage import add_minimum_area_coverage
from .constraints.room_size_hierarchy_constraints import add_room_size_hierarchy
from .constraints.compact_layout import add_center_proximity_objective


class FloorPlanGenerator:
    def __init__(self, requirements: FpgRequirements):
        """Initialize generator from a full requirements object.

        ``requirements`` bundles room specifications and configuration
        parameters (coverage, aspect ratios, floor size, etc.).

        We first normalize the incoming data with ``rules.normalize_requirements``
        so that downstream code can rely on sensible numeric values.
        """
        # apply preprocessing rules before touching the config
        requirements = normalize_requirements(requirements)

        cfg = requirements.config
        # store basic properties for later use (floats now allowed)
        self.floor_plan_width: float = cfg.floor_plan_width
        self.floor_plan_height: float = cfg.floor_plan_height
        self.min_coverage: float = cfg.min_coverage

        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()

        # convert room data objects directly to solver rooms
        self.rooms: list[Room] = [
            Room(r.name, r.min_w, r.min_h, r.max_w, r.max_h, r.type)
            for r in requirements.rooms
        ]

    def generate(self) -> bool:
        """Build and solve the floor plan. Returns True if a solution was found."""
        # 1. Initialize CP-SAT variables for every room
        # OR-Tools only accepts integer bounds, so cast the float dimensions.
        w_int = int(self.floor_plan_width)
        h_int = int(self.floor_plan_height)
        for room in self.rooms:
            room.create_variables(self.model, w_int, h_int)

        # 2. Add constraints
        add_basic_constraints(self.model, self.rooms)
        add_kitchen_living_adjacency(self.model, self.rooms)
        add_minimum_area_coverage(
            self.model,
            self.rooms,
            self.floor_plan_width,
            self.floor_plan_height,
            self.min_coverage,
        )
        add_room_size_hierarchy(self.model, self.rooms)

        # Soft objective: minimise total Manhattan distance of every room
        # centre from the floor centre so rooms cluster toward the middle.
        cost = add_center_proximity_objective(
            self.model,
            self.rooms,
            self.floor_plan_width,
            self.floor_plan_height,
        )
        self.model.Minimize(cost)  # type: ignore[attr-defined]

        # 3. Solve
        self.solver.parameters.max_time_in_seconds = 1.0
        self.solver.parameters.random_seed = random.randint(0, 1000)
        self.solver.parameters.randomize_search = True
        status = self.solver.Solve(self.model)

        return status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
        

    def get_solution(self) -> list[dict]:
        """Extract room placements from the solver after a successful solve."""
        results = []
        for room in self.rooms:
            # the variables are created during `generate`; make sure they exist so
            # the type checker can narrow Optional[IntVar] -> IntVar and avoid
            # passing None into solver.Value.
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

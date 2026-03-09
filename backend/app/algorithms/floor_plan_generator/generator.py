from ortools.sat.python import cp_model
import random
from .models.room import Room
from .constraints.basic_constraints import add_basic_constraints
from .constraints.adjacency_constraints import add_kitchen_living_adjacency
from .constraints.floor_area_coverage import add_minimum_area_coverage
from .constraints.room_size_hierarchy_constraints import add_room_size_hierarchy
from .config import MIN_COVERAGE


class FloorPlanGenerator:
    def __init__(self, boundary_width: int, boundary_height: int, rooms_data: list):
        self.boundary_width = boundary_width
        self.boundary_height = boundary_height
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()

        self.rooms: list[Room] = []
        for data in rooms_data:
            new_room = Room(
                data["name"],
                data["min_w"],
                data["min_h"],
                data["max_w"],
                data["max_h"],
                data["type"],
            )
            self.rooms.append(new_room)

    def generate(self) -> bool:
        """Build and solve the floor plan. Returns True if a solution was found."""
        # 1. Initialize CP-SAT variables for every room
        for room in self.rooms:
            room.create_variables(self.model, self.boundary_width, self.boundary_height)

        # 2. Add constraints
        add_basic_constraints(self.model, self.rooms)
        add_kitchen_living_adjacency(self.model, self.rooms)
        add_minimum_area_coverage(
            self.model,
            self.rooms,
            self.boundary_width,
            self.boundary_height,
            MIN_COVERAGE,
        )
        add_room_size_hierarchy(self.model, self.rooms)

        # 3. Solve
        self.solver.parameters.random_seed = random.randint(0, 1000)
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
            print("Raw Solver Results for room", room.name)
            for key, val in results[-1].items():
                print(f"    {key}: {val}")
        return results

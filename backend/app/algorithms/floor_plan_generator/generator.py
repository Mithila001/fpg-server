from ortools.sat.python import cp_model
import random
from .models.room import Room
from .constraints.basic_constraints import add_basic_constraints
from .constraints.adjacency_constraints import add_kitchen_living_adjacency
from .constraints.floor_area_coverage import add_minimum_area_coverage
from .constraints.room_size_hierarchy_constraints import add_room_size_hierarchy
from .config import MIN_COVERAGE


class FloorPlanGenerator:
    def __init__(self, width: int, height: int, rooms_data: list):
        self.width = width
        self.height = height
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
            room.create_variables(self.model, self.width, self.height)

        # 2. Add constraints
        add_basic_constraints(self.model, self.rooms)
        add_kitchen_living_adjacency(self.model, self.rooms)
        add_minimum_area_coverage(
            self.model, self.rooms, self.width, self.height, MIN_COVERAGE
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

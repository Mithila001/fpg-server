from ortools.sat.python import cp_model
import random
from .models.room import Room
from .constraints.basic_constraints import add_basic_constraints
from .constraints.adjacency_constraints import add_kitchen_living_adjacency
from .constraints.floor_area_coverage import add_minimum_area_coverage
from .constraints.room_size_hierarchy_constraints import add_room_size_hierarchy


class FloorPlanGenerator:
    def __init__(self, width, height, rooms_data):
        self.width = width
        self.height = height
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()

        # Convert raw dictionaries from config into Room Objects
        self.rooms: list[Room] = []
        for data in rooms_data:
            new_room = Room(
                data["name"],
                data["min_w"],
                data["min_h"],
                data["max_w"],
                data["max_h"],
                data["type"],
            )  # Goal here is not to populate all attributes yet, just what we already knows (tip: from config file).
            self.rooms.append(new_room)

    def generate(self):
        """Main process to build and solve the plan."""
        # 1. Initialize variables for every room object
        for room in self.rooms:
            room.create_variables(self.model, self.width, self.height)

        # 2. Add Constraints (Passing the list of room objects)
        add_basic_constraints(self.model, self.rooms)
        add_kitchen_living_adjacency(self.model, self.rooms)
        add_minimum_area_coverage(self.model, self.rooms, self.width, self.height)
        add_room_size_hierarchy(self.model, self.rooms)

        # 3. Solve
        self.solver.parameters.random_seed = random.randint(0, 1000)
        status = self.solver.Solve(self.model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            return True
        return False

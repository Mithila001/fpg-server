from ortools.sat.python import cp_model
from typing import Optional


class Room:
    def __init__(self, name: str, min_w: int, min_h: int, max_w: int, max_h: int, type: str):
        self.name = name
        self.min_w = min_w
        self.min_h = min_h
        self.max_w = max_w
        self.max_h = max_h
        self.type = type

        # OR-Tools Variables (populated by create_variables)
        self.x: Optional[cp_model.IntVar] = None
        self.y: Optional[cp_model.IntVar] = None
        self.w: Optional[cp_model.IntVar] = None
        self.h: Optional[cp_model.IntVar] = None
        self.x_end: Optional[cp_model.IntVar] = None
        self.y_end: Optional[cp_model.IntVar] = None
        self.area: Optional[cp_model.IntVar] = None
        self.x_interval: Optional[cp_model.IntervalVar] = None
        self.y_interval: Optional[cp_model.IntervalVar] = None

    def create_variables(self, model: cp_model.CpModel, land_width: int, land_height: int):
        """Creates CP-SAT variables for this room."""
        self.x = model.NewIntVar(0, land_width - self.min_w, f"{self.name}_x")
        self.y = model.NewIntVar(0, land_height - self.min_h, f"{self.name}_y")

        self.w = model.NewIntVar(self.min_w, self.max_w, f"{self.name}_w")
        self.h = model.NewIntVar(self.min_h, self.max_h, f"{self.name}_h")

        self.area = model.NewIntVar(0, land_width * land_height, f"{self.name}_area")
        model.AddMultiplicationEquality(self.area, [self.w, self.h])

        self.x_end = model.NewIntVar(0, land_width, f"{self.name}_x_end")
        self.y_end = model.NewIntVar(0, land_height, f"{self.name}_y_end")

        self.x_interval = model.NewIntervalVar(
            self.x, self.w, self.x_end, f"{self.name}_x_interval"
        )
        self.y_interval = model.NewIntervalVar(
            self.y, self.h, self.y_end, f"{self.name}_y_interval"
        )

from typing import List

from ortools.sat.python import cp_model

from ...solver_models.room import Room


def add_center_proximity_objective(
    model: cp_model.CpModel,
    rooms: List[Room],
    floor_width: float,
    floor_height: float,
) -> cp_model.LinearExprT:
    w_int = int(floor_width)
    h_int = int(floor_height)

    max_dx = w_int * 2
    max_dy = h_int * 2

    cost_terms: List[cp_model.IntVar] = []

    for room in rooms:
        dx = model.NewIntVar(-max_dx, max_dx, f"{room.name}_centre_dx")  # type: ignore
        dy = model.NewIntVar(-max_dy, max_dy, f"{room.name}_centre_dy")  # type: ignore
        abs_dx = model.NewIntVar(0, max_dx, f"{room.name}_centre_abs_dx")  # type: ignore
        abs_dy = model.NewIntVar(0, max_dy, f"{room.name}_centre_abs_dy")  # type: ignore

        model.Add(dx == room.x + room.x_end - w_int)  # type: ignore
        model.Add(dy == room.y + room.y_end - h_int)  # type: ignore

        model.AddAbsEquality(abs_dx, dx)  # type: ignore[attr-defined]
        model.AddAbsEquality(abs_dy, dy)  # type: ignore[attr-defined]

        cost_terms.append(abs_dx)
        cost_terms.append(abs_dy)

    return cp_model.LinearExpr.Sum(cost_terms)  # type: ignore

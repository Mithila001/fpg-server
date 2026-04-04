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
    _ = floor_height

    max_dx = w_int * 2

    cost_terms: List[cp_model.LinearExprT] = []

    for room in rooms:
        dx = model.NewIntVar(-max_dx, max_dx, f"{room.name}_centre_dx")  # type: ignore
        abs_dx = model.NewIntVar(0, max_dx, f"{room.name}_centre_abs_dx")  # type: ignore

        model.Add(dx == room.x + room.x_end - w_int)  # type: ignore

        model.AddAbsEquality(abs_dx, dx)  # type: ignore[attr-defined]

        cost_terms.append(abs_dx)
        cost_terms.append(room.y)  # type: ignore[arg-type]

    return cp_model.LinearExpr.Sum(cost_terms)  # type: ignore

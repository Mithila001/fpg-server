from ortools.sat.python import cp_model
from typing import List
from ..solver_models.room import Room


def add_center_proximity_objective(
    model: cp_model.CpModel,
    rooms: List[Room],
    floor_width: float,
    floor_height: float,
) -> cp_model.LinearExprT:
    """Build a minimisation cost that pulls every room toward the floor centre.

    Rather than dividing by 2 to get fractional centres, we work in *doubled*
    coordinates so that integer arithmetic is exact:

        2 * room_cx  =  room.x + room.x_end
        2 * floor_cx =  floor_width            (an integer)

    The signed offsets are therefore:

        dx  =  (room.x + room.x_end) - floor_width
        dy  =  (room.y + room.y_end) - floor_height

    and the cost per room is ``|dx| + |dy|``.  Summing over all rooms gives the
    total cost expression that the caller must pass to ``model.Minimize()``.

    Args:
        model:        The CP-SAT model.
        rooms:        List of rooms whose variables have already been created.
        floor_width:  Width of the floor plan (will be cast to int).
        floor_height: Height of the floor plan (will be cast to int).

    Returns:
        A linear expression representing the total centre-proximity cost.
        Pass it directly to ``model.Minimize(cost)``.
    """
    w_int = int(floor_width)
    h_int = int(floor_height)

    # worst-case absolute offset is 2 * floor dimension
    max_dx = w_int * 2
    max_dy = h_int * 2

    cost_terms: List[cp_model.IntVar] = []

    for room in rooms:
        dx = model.NewIntVar(-max_dx, max_dx, f"{room.name}_centre_dx")  # type: ignore
        dy = model.NewIntVar(-max_dy, max_dy, f"{room.name}_centre_dy")  # type: ignore
        abs_dx = model.NewIntVar(0, max_dx, f"{room.name}_centre_abs_dx")  # type: ignore
        abs_dy = model.NewIntVar(0, max_dy, f"{room.name}_centre_abs_dy")  # type: ignore

        # signed offset (doubled coordinates – no integer division required)
        model.Add(dx == room.x + room.x_end - w_int)  # type: ignore
        model.Add(dy == room.y + room.y_end - h_int)  # type: ignore

        model.AddAbsEquality(abs_dx, dx)  # type: ignore[attr-defined]
        model.AddAbsEquality(abs_dy, dy)  # type: ignore[attr-defined]

        cost_terms.append(abs_dx)
        cost_terms.append(abs_dy)

    return cp_model.LinearExpr.Sum(cost_terms)  # type: ignore

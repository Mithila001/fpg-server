from typing import List

from ortools.sat.python import cp_model

from app.core.fpg_rooms.config_fpg import BATHROOM_LOCATION_WEIGHT

from ...solver_models.room import Room


def build_bathroom_location_preference_penalty(
    model: cp_model.CpModel,
    rooms: List[Room],
    floor_height: float,
    bathroom_weight: int = BATHROOM_LOCATION_WEIGHT,
) -> cp_model.LinearExprT:
    if bathroom_weight <= 0:
        bathroom_weight = 1

    h_int = int(floor_height)
    max_center_y2 = h_int * 2

    terms: List[cp_model.LinearExprT] = []
    for room in rooms:
        if room.type != "bathroom":
            continue

        penalty = max_center_y2 - (room.y + room.y_end)  # type: ignore
        terms.append(penalty * bathroom_weight)

    if not terms:
        return 0

    return cp_model.LinearExpr.Sum(terms)  # type: ignore

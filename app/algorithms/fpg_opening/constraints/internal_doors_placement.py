from __future__ import annotations

from ortools.sat.python import cp_model

from app.algorithms.types.solvers import (
    InternalDoorCandidate,
    InternalDoorDecisionVars,
)
from app.core.fpg_opening_config import (
    INTERNAL_DOOR_ALLOWED_ROOM_PAIRS,
    MAX_INTERNAL_DOORS_BY_ROOM_TYPE,
    normalize_room_type,
)


# Room types are normalized to lowercase by normalize_room_type(), so these
# canonical pairs are stored accordingly (e.g. "livingRoom" -> "livingroom").
def _is_allowed_connection(room_type_a: str, room_type_b: str) -> bool:
    a = normalize_room_type(room_type_a)
    b = normalize_room_type(room_type_b)

    # attachedBathroom can only have an internal door to a bedroom.
    if a == "attachedbathroom" or b == "attachedbathroom":
        return frozenset((a, b)) == frozenset(("bedroom", "attachedbathroom"))

    if a == "hallway" or b == "hallway":
        return True

    return frozenset((a, b)) in INTERNAL_DOOR_ALLOWED_ROOM_PAIRS


def add_internal_doors_placement_constraint(
    model: cp_model.CpModel,
    candidates: list[InternalDoorCandidate],
) -> InternalDoorDecisionVars:
    """Whitelist internal door pairings by room type.

    This enforces strict allowed room-type connections and per-room limits by
    room type for selected internal doors.
    """
    selected_vars: list[cp_model.IntVar] = []
    room_incident_selection_vars: dict[str, list[cp_model.IntVar]] = {}
    room_name_to_type: dict[str, str] = {}
    bedroom_to_hallway_vars: dict[str, list[cp_model.IntVar]] = {}
    bedroom_to_livingroom_vars: dict[str, list[cp_model.IntVar]] = {}

    for index, candidate in enumerate(candidates):
        selected = model.NewBoolVar(f"internal_door_selected_{index}")  # type: ignore
        selected_vars.append(selected)

        if _is_allowed_connection(candidate["room_a_type"], candidate["room_b_type"]):
            room_a_name = candidate["room_a_name"]
            room_b_name = candidate["room_b_name"]
            room_a_type = normalize_room_type(candidate["room_a_type"])
            room_b_type = normalize_room_type(candidate["room_b_type"])
            room_incident_selection_vars.setdefault(room_a_name, []).append(selected)
            room_incident_selection_vars.setdefault(room_b_name, []).append(selected)
            room_name_to_type[room_a_name] = room_a_type
            room_name_to_type[room_b_name] = room_b_type

            if room_a_type == "bedroom" and room_b_type == "hallway":
                bedroom_to_hallway_vars.setdefault(room_a_name, []).append(selected)
            elif room_b_type == "bedroom" and room_a_type == "hallway":
                bedroom_to_hallway_vars.setdefault(room_b_name, []).append(selected)

            if room_a_type == "bedroom" and room_b_type == "livingroom":
                bedroom_to_livingroom_vars.setdefault(room_a_name, []).append(selected)
            elif room_b_type == "bedroom" and room_a_type == "livingroom":
                bedroom_to_livingroom_vars.setdefault(room_b_name, []).append(selected)

        else:
            model.Add(selected == 0)

    for room_name, incident_vars in room_incident_selection_vars.items():
        room_type = room_name_to_type.get(room_name)
        if room_type is None:
            continue

        max_doors = MAX_INTERNAL_DOORS_BY_ROOM_TYPE.get(room_type)
        if max_doors is None:
            continue

        model.Add(sum(incident_vars) <= max_doors)

    # A bedroom gets at most one social/internal door among hallway or livingRoom.
    # attachedBathroom is tracked separately so a bedroom can still have one
    # attachedBathroom door in addition to one social door (total max stays 2).
    for bedroom_name, room_type in room_name_to_type.items():
        if room_type != "bedroom":
            continue

        social_vars = bedroom_to_hallway_vars.get(
            bedroom_name, []
        ) + bedroom_to_livingroom_vars.get(bedroom_name, [])
        if social_vars:
            model.Add(sum(social_vars) <= 1)

    hallway_priority_vars: list[cp_model.IntVar] = []
    for hallway_vars in bedroom_to_hallway_vars.values():
        hallway_priority_vars.extend(hallway_vars)

    if selected_vars:
        total_selected = cp_model.LinearExpr.Sum(selected_vars)
        total_hallway_priority = cp_model.LinearExpr.Sum(hallway_priority_vars)
        # Keep maximizing total doors first, then prefer hallway ties for bedrooms.
        model.Maximize(total_selected * 1000 + total_hallway_priority)

    return {"selected": selected_vars}

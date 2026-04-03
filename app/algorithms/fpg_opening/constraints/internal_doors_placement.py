from __future__ import annotations

from ortools.sat.python import cp_model

from app.algorithms.fpg_opening.types.opening_solver import InternalDoorCandidate, InternalDoorDecisionVars


# Room types are normalized to lowercase by _normalize_room_type(), so these
# canonical pairs are stored accordingly (e.g. "livingRoom" -> "livingroom").
_NON_HALLWAY_ALLOWED_PAIRS = {
    frozenset(("bedroom", "livingroom")),
    frozenset(("kitchen", "livingroom")),
    frozenset(("bathroom", "livingroom")),
    frozenset(("bedroom", "attachedBathroom")),
}

_MAX_INTERNAL_DOORS_PER_ROOM_TYPE = {
    "bedroom": 2,
    "bathroom": 1,
    "livingroom": 10,
    "hallway": 10,
    "kitchen": 2,
    "attachedBathroom":1
}


def _normalize_room_type(room_type: str) -> str:
    return room_type.strip().lower()


def _is_allowed_connection(room_type_a: str, room_type_b: str) -> bool:
    a = _normalize_room_type(room_type_a)
    b = _normalize_room_type(room_type_b)

    if a == "hallway" or b == "hallway":
        return True

    return frozenset((a, b)) in _NON_HALLWAY_ALLOWED_PAIRS


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

    for index, candidate in enumerate(candidates):
        selected = model.NewBoolVar(f"internal_door_selected_{index}")  # type: ignore
        selected_vars.append(selected)

        if _is_allowed_connection(candidate["room_a_type"], candidate["room_b_type"]):
            room_a_name = candidate["room_a_name"]
            room_b_name = candidate["room_b_name"]
            room_incident_selection_vars.setdefault(room_a_name, []).append(selected)
            room_incident_selection_vars.setdefault(room_b_name, []).append(selected)
            room_name_to_type[room_a_name] = _normalize_room_type(candidate["room_a_type"])
            room_name_to_type[room_b_name] = _normalize_room_type(candidate["room_b_type"])
        else:
            model.Add(selected == 0)

    for room_name, incident_vars in room_incident_selection_vars.items():
        room_type = room_name_to_type.get(room_name)
        if room_type is None:
            continue

        max_doors = _MAX_INTERNAL_DOORS_PER_ROOM_TYPE.get(room_type)
        if max_doors is None:
            continue

        model.Add(sum(incident_vars) <= max_doors)

    if selected_vars:
        model.Maximize(sum(selected_vars))

    return {"selected": selected_vars}
from __future__ import annotations

from ortools.sat.python import cp_model

from app.algorithms.fpg_opening.types.opening_solver import InternalDoorCandidate, InternalDoorDecisionVars


# Room types are normalized to lowercase by _normalize_room_type(), so these
# canonical pairs are stored accordingly (e.g. "livingRoom" -> "livingroom").
_NON_HALLWAY_ALLOWED_PAIRS = {
    frozenset(("bedroom", "livingroom")),
    frozenset(("kitchen", "livingroom")),
    frozenset(("bathroom", "livingroom")),
    frozenset(("bedroom", "bathroom")),
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

    This enforces strict allowed room-type connections. Forbidden pairings are
    forced to 0, while allowed pairings are selected.
    """
    selected_vars: list[cp_model.IntVar] = []

    for index, candidate in enumerate(candidates):
        selected = model.NewBoolVar(f"internal_door_selected_{index}")  # type: ignore
        selected_vars.append(selected)

        if _is_allowed_connection(candidate["room_a_type"], candidate["room_b_type"]):
            model.Add(selected == 1)
        else:
            model.Add(selected == 0)

    return {"selected": selected_vars}
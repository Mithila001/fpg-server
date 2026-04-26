from typing import List, Sequence

from ortools.sat.python import cp_model

from app.core.fpg_rooms.config_fpg import DEFAULT_ADJACENCY_MIN_OVERLAP
from app.schemas.db.room_relations_constraints import RoomRelationsConstraintBase

from ...solver_models.room import Room
from ..hard.room_adjacency_hard import add_conditional_room_touch_constraint


def build_soft_room_adjacency_preference_vars(
    model: cp_model.CpModel,
    rooms_list: List[Room],
    soft_relations: Sequence[RoomRelationsConstraintBase] | None = None,
    min_overlap: int = DEFAULT_ADJACENCY_MIN_OVERLAP,
) -> List[cp_model.IntVar]:
    preference_vars: List[cp_model.IntVar] = []

    if not soft_relations:
        return preference_vars

    for room in rooms_list:
        matching_rules = [
            relation for relation in soft_relations if relation.room_type == room.type
        ]
        if not matching_rules:
            continue

        for rule in matching_rules:
            related_types = rule.related_room or []
            if not related_types:
                continue

            all_candidates: List[Room] = []
            for required_type in related_types:
                candidates = [
                    candidate
                    for candidate in rooms_list
                    if candidate.type == required_type and candidate.name != room.name
                ]
                all_candidates.extend(candidates)

            for candidate in all_candidates:
                is_adj = model.NewBoolVar(f"soft_is_adj_{room.name}_{candidate.name}")  # type: ignore
                preference_vars.append(is_adj)
                add_conditional_room_touch_constraint(
                    model,
                    room,
                    candidate,
                    enforcer=is_adj,
                    min_overlap=min_overlap,
                )

    return preference_vars

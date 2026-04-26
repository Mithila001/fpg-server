from typing import Any, List, Sequence

from ortools.sat.python import cp_model

from app.core.fpg_rooms.config_fpg import DEFAULT_ADJACENCY_MIN_OVERLAP
from app.schemas.db.room_relations_constraints import RoomRelationsConstraintBase

from ...solver_models.room import Room


def add_conditional_room_touch_constraint(
    model: Any,
    room1: Room,
    room2: Room,
    enforcer: Any | None = None,
    min_overlap: int = DEFAULT_ADJACENCY_MIN_OVERLAP,
) -> None:
    suffix = f"{room1.name}_{room2.name}"

    touch_right = model.NewBoolVar(f"touch_right_{suffix}")  # type: ignore
    touch_left = model.NewBoolVar(f"touch_left_{suffix}")  # type: ignore
    touch_top = model.NewBoolVar(f"touch_top_{suffix}")  # type: ignore
    touch_bottom = model.NewBoolVar(f"touch_bottom_{suffix}")  # type: ignore

    conds: List[Any] = []
    if enforcer is not None:
        conds.append(enforcer)

    model.Add(room1.x == room2.x_end).OnlyEnforceIf(conds + [touch_right])  # type: ignore
    model.Add(room1.x != room2.x_end).OnlyEnforceIf(conds + [touch_right.Not()])  # type: ignore

    model.Add(room1.x_end == room2.x).OnlyEnforceIf(conds + [touch_left])  # type: ignore
    model.Add(room1.x_end != room2.x).OnlyEnforceIf(conds + [touch_left.Not()])  # type: ignore

    model.Add(room1.y == room2.y_end).OnlyEnforceIf(conds + [touch_top])  # type: ignore
    model.Add(room1.y != room2.y_end).OnlyEnforceIf(conds + [touch_top.Not()])  # type: ignore

    model.Add(room1.y_end == room2.y).OnlyEnforceIf(conds + [touch_bottom])  # type: ignore
    model.Add(room1.y_end != room2.y).OnlyEnforceIf(conds + [touch_bottom.Not()])  # type: ignore

    if enforcer is not None:
        model.AddBoolOr(
            [touch_right, touch_left, touch_top, touch_bottom]
        ).OnlyEnforceIf(enforcer)  # type: ignore[attr-defined]
    else:
        model.AddBoolOr([touch_right, touch_left, touch_top, touch_bottom])  # type: ignore[attr-defined]

    for touch in (touch_right, touch_left):
        model.Add(room1.y + min_overlap <= room2.y_end).OnlyEnforceIf(conds + [touch])  # type: ignore
        model.Add(room2.y + min_overlap <= room1.y_end).OnlyEnforceIf(conds + [touch])  # type: ignore

    for touch in (touch_top, touch_bottom):
        model.Add(room1.x + min_overlap <= room2.x_end).OnlyEnforceIf(conds + [touch])  # type: ignore
        model.Add(room2.x + min_overlap <= room1.x_end).OnlyEnforceIf(conds + [touch])  # type: ignore


def add_hard_and_room_adjacency_constraints(
    model: Any,
    rooms_list: List[Room],
    hard_and_relations: Sequence[RoomRelationsConstraintBase],
    min_overlap: int = DEFAULT_ADJACENCY_MIN_OVERLAP,
) -> None:
    for room in rooms_list:
        matching_rules = [
            rel for rel in hard_and_relations if rel.room_type == room.type
        ]
        if not matching_rules:
            continue

        for rule in matching_rules:
            related_types = rule.related_room or []
            if not related_types:
                continue

            for required_type in related_types:
                candidates = [
                    candidate
                    for candidate in rooms_list
                    if candidate.type == required_type and candidate.name != room.name
                ]
                if not candidates:
                    model.AddBoolOr([])
                    continue

                adj_switches: List[Any] = []
                for candidate in candidates:
                    is_adj = model.NewBoolVar(f"is_adj_{room.name}_{candidate.name}")  # type: ignore
                    adj_switches.append(is_adj)
                    add_conditional_room_touch_constraint(
                        model,
                        room,
                        candidate,
                        enforcer=is_adj,
                        min_overlap=min_overlap,
                    )

                model.AddBoolOr(adj_switches)  # type: ignore


def add_hard_or_room_adjacency_constraints(
    model: Any,
    rooms_list: List[Room],
    hard_or_relations: Sequence[RoomRelationsConstraintBase],
    min_overlap: int = DEFAULT_ADJACENCY_MIN_OVERLAP,
) -> None:
    for room in rooms_list:
        matching_rules = [
            rel for rel in hard_or_relations if rel.room_type == room.type
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

            if not all_candidates:
                model.AddBoolOr([])
                continue

            adj_switches: List[Any] = []
            for candidate in all_candidates:
                is_adj = model.NewBoolVar(f"is_adj_{room.name}_{candidate.name}")  # type: ignore
                adj_switches.append(is_adj)
                add_conditional_room_touch_constraint(
                    model,
                    room,
                    candidate,
                    enforcer=is_adj,
                    min_overlap=min_overlap,
                )

            model.AddBoolOr(adj_switches)  # type: ignore


def apply_hard_room_adjacency_constraints(
    model: Any,
    rooms_list: List[Room],
    hard_and_relations: Sequence[RoomRelationsConstraintBase] | None = None,
    hard_or_relations: Sequence[RoomRelationsConstraintBase] | None = None,
    min_overlap: int = DEFAULT_ADJACENCY_MIN_OVERLAP,
) -> None:
    if hard_and_relations:
        add_hard_and_room_adjacency_constraints(
            model,
            rooms_list,
            hard_and_relations,
            min_overlap=min_overlap,
        )

    if hard_or_relations:
        add_hard_or_room_adjacency_constraints(
            model,
            rooms_list,
            hard_or_relations,
            min_overlap=min_overlap,
        )

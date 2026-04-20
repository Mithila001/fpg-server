"""Hard dining-room relation constraints.

For each diningRoom:
- must touch a livingRoom directly OR through one hallway hop
- must touch a kitchen directly OR through one hallway hop
"""

from __future__ import annotations

from ortools.sat.python import cp_model

from app.core.fpg_rooms.config_fpg import GENERATOR_ADJACENCY_MIN_OVERLAP

from ...solver_models.room import Room
from .room_adjacency_hard import add_conditional_room_touch_constraint


def _require_room_geometry(room: Room) -> None:
    if (
        room.x is None
        or room.y is None
        or room.x_end is None
        or room.y_end is None
    ):
        raise ValueError(
            f"Room '{room.name}' ({room.type}) has null geometry vars before adjacency encoding."
        )


def _adjacent_literal(
    model: cp_model.CpModel,
    room_a: Room,
    room_b: Room,
    *,
    min_overlap: int,
    name: str,
) -> cp_model.BoolVar:
    _require_room_geometry(room_a)
    _require_room_geometry(room_b)

    adjacent = model.NewBoolVar(name)
    add_conditional_room_touch_constraint(
        model,
        room_a,
        room_b,
        enforcer=adjacent,
        min_overlap=min_overlap,
    )
    return adjacent


def _and_literal(
    model: cp_model.CpModel,
    left: cp_model.BoolVar,
    right: cp_model.BoolVar,
    *,
    name: str,
) -> cp_model.BoolVar:
    both = model.NewBoolVar(name)
    model.AddBoolAnd([left, right]).OnlyEnforceIf(both)
    model.AddBoolOr([left.Not(), right.Not()]).OnlyEnforceIf(both.Not())
    return both


def _build_target_paths(
    model: cp_model.CpModel,
    dining_room: Room,
    target_rooms: list[Room],
    hallway_rooms: list[Room],
    *,
    min_overlap: int,
    target_label: str,
) -> list[cp_model.BoolVar]:
    paths: list[cp_model.BoolVar] = []

    for target in target_rooms:
        paths.append(
            _adjacent_literal(
                model,
                dining_room,
                target,
                min_overlap=min_overlap,
                name=f"hard_dining_direct_{target_label}_{dining_room.name}_{target.name}",
            )
        )

    for hallway in hallway_rooms:
        for target in target_rooms:
            dining_to_hallway = _adjacent_literal(
                model,
                dining_room,
                hallway,
                min_overlap=min_overlap,
                name=f"hard_dining_to_hall_{dining_room.name}_{hallway.name}_{target_label}_{target.name}",
            )
            hallway_to_target = _adjacent_literal(
                model,
                hallway,
                target,
                min_overlap=min_overlap,
                name=f"hard_hall_to_{target_label}_{hallway.name}_{target.name}_{dining_room.name}",
            )
            paths.append(
                _and_literal(
                    model,
                    dining_to_hallway,
                    hallway_to_target,
                    name=f"hard_dining_via_hall_{target_label}_{dining_room.name}_{hallway.name}_{target.name}",
                )
            )

    return paths


def add_hard_dining_room_relation_constraint(
    model: cp_model.CpModel,
    rooms: list[Room],
    min_overlap: int = GENERATOR_ADJACENCY_MIN_OVERLAP,
) -> None:
    if rooms is None:
        raise ValueError("rooms cannot be None")

    dining_rooms = [room for room in rooms if room.type == "diningRoom"]
    if not dining_rooms:
        return

    living_rooms = [room for room in rooms if room.type == "livingRoom"]
    kitchen_rooms = [room for room in rooms if room.type == "kitchen"]
    hallway_rooms = [room for room in rooms if room.type == "hallway"]

    for dining_room in dining_rooms:
        living_paths = _build_target_paths(
            model,
            dining_room,
            living_rooms,
            hallway_rooms,
            min_overlap=min_overlap,
            target_label="living",
        )
        kitchen_paths = _build_target_paths(
            model,
            dining_room,
            kitchen_rooms,
            hallway_rooms,
            min_overlap=min_overlap,
            target_label="kitchen",
        )

        # Keep hard semantics: if no valid target candidates exist, this becomes infeasible.
        model.AddBoolOr(living_paths)
        model.AddBoolOr(kitchen_paths)

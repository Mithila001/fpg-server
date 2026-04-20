import pytest
from ortools.sat.python import cp_model

from app.algorithms.fpg_rooms.constraints.hard.hard_dining_room_relation import (
    add_hard_dining_room_relation_constraint,
)
from app.algorithms.fpg_rooms.solver_models.room import Room


def _fixed_room(
    model: cp_model.CpModel,
    *,
    name: str,
    room_type: str,
    x: int,
    y: int,
    w: int,
    h: int,
    land_w: int = 160,
    land_h: int = 160,
) -> Room:
    room = Room(name=name, min_w=w, min_h=h, max_w=w, max_h=h, type=room_type)
    room.create_variables(model, land_w, land_h)
    model.Add(room.x == x)
    model.Add(room.y == y)
    return room


def test_dining_relation_satisfied_with_direct_adjacency() -> None:
    model = cp_model.CpModel()

    dining = _fixed_room(
        model,
        name="dining_1",
        room_type="diningRoom",
        x=10,
        y=10,
        w=20,
        h=20,
    )
    living = _fixed_room(
        model,
        name="living_1",
        room_type="livingRoom",
        x=30,
        y=10,
        w=20,
        h=20,
    )
    kitchen = _fixed_room(
        model,
        name="kitchen_1",
        room_type="kitchen",
        x=10,
        y=30,
        w=20,
        h=20,
    )

    add_hard_dining_room_relation_constraint(model, [dining, living, kitchen], min_overlap=5)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_dining_relation_satisfied_with_hallway_path() -> None:
    model = cp_model.CpModel()

    dining = _fixed_room(
        model,
        name="dining_1",
        room_type="diningRoom",
        x=10,
        y=10,
        w=20,
        h=20,
    )
    hallway_living = _fixed_room(
        model,
        name="hallway_living_1",
        room_type="hallway",
        x=30,
        y=10,
        w=20,
        h=20,
    )
    living = _fixed_room(
        model,
        name="living_1",
        room_type="livingRoom",
        x=50,
        y=10,
        w=20,
        h=20,
    )
    hallway_kitchen = _fixed_room(
        model,
        name="hallway_kitchen_1",
        room_type="hallway",
        x=10,
        y=30,
        w=20,
        h=20,
    )
    kitchen = _fixed_room(
        model,
        name="kitchen_1",
        room_type="kitchen",
        x=10,
        y=50,
        w=20,
        h=20,
    )

    add_hard_dining_room_relation_constraint(
        model,
        [dining, hallway_living, living, hallway_kitchen, kitchen],
        min_overlap=5,
    )

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_dining_relation_infeasible_when_no_living_or_hallway_path() -> None:
    model = cp_model.CpModel()

    dining = _fixed_room(
        model,
        name="dining_1",
        room_type="diningRoom",
        x=10,
        y=10,
        w=20,
        h=20,
    )
    living = _fixed_room(
        model,
        name="living_1",
        room_type="livingRoom",
        x=80,
        y=80,
        w=20,
        h=20,
    )
    kitchen = _fixed_room(
        model,
        name="kitchen_1",
        room_type="kitchen",
        x=10,
        y=30,
        w=20,
        h=20,
    )

    add_hard_dining_room_relation_constraint(model, [dining, living, kitchen], min_overlap=5)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status == cp_model.INFEASIBLE


def test_dining_relation_noop_when_no_dining_room() -> None:
    model = cp_model.CpModel()

    living = _fixed_room(
        model,
        name="living_1",
        room_type="livingRoom",
        x=10,
        y=10,
        w=20,
        h=20,
    )
    kitchen = _fixed_room(
        model,
        name="kitchen_1",
        room_type="kitchen",
        x=40,
        y=10,
        w=20,
        h=20,
    )

    add_hard_dining_room_relation_constraint(model, [living, kitchen], min_overlap=5)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_dining_relation_raises_on_null_geometry() -> None:
    model = cp_model.CpModel()

    dining = Room(name="dining_1", min_w=10, min_h=10, max_w=10, max_h=10, type="diningRoom")
    living = Room(name="living_1", min_w=10, min_h=10, max_w=10, max_h=10, type="livingRoom")
    kitchen = Room(name="kitchen_1", min_w=10, min_h=10, max_w=10, max_h=10, type="kitchen")

    with pytest.raises(ValueError):
        add_hard_dining_room_relation_constraint(model, [dining, living, kitchen], min_overlap=5)

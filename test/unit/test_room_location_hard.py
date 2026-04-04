from ortools.sat.python import cp_model

from app.algorithms.fpg_rooms.constraints.hard.room_location_hard import (
    add_living_room_bottom_most_constraint,
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
    land_w: int = 120,
    land_h: int = 120,
) -> Room:
    room = Room(name=name, min_w=w, min_h=h, max_w=w, max_h=h, type=room_type)
    room.create_variables(model, land_w, land_h)
    model.Add(room.x == x)
    model.Add(room.y == y)
    return room


def test_room_location_hard_veranda_anchor_allows_taller_rooms() -> None:
    model = cp_model.CpModel()

    veranda = _fixed_room(
        model,
        name="veranda_1",
        room_type="veranda",
        x=0,
        y=0,
        w=20,
        h=24,
    )
    garage = _fixed_room(
        model,
        name="garage_1",
        room_type="garage",
        x=20,
        y=0,
        w=30,
        h=50,
    )

    add_living_room_bottom_most_constraint(model, [veranda, garage])

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_room_location_hard_living_fallback_keeps_living_room_frontmost() -> None:
    model = cp_model.CpModel()

    living = _fixed_room(
        model,
        name="living_1",
        room_type="livingRoom",
        x=0,
        y=0,
        w=20,
        h=20,
    )
    bedroom = _fixed_room(
        model,
        name="bedroom_1",
        room_type="bedroom",
        x=0,
        y=10,
        w=20,
        h=10,
    )

    add_living_room_bottom_most_constraint(model, [living, bedroom])

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

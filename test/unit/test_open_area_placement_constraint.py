from ortools.sat.python import cp_model

from app.algorithms.fpg_rooms.constraints.hard.open_area_placement import (
    add_open_area_placement_constraints,
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


def test_open_area_placement_veranda_feasible_when_front_open_and_one_side_open() -> None:
    model = cp_model.CpModel()

    veranda = _fixed_room(
        model,
        name="veranda_1",
        room_type="veranda",
        x=20,
        y=20,
        w=20,
        h=20,
    )
    # Back attachment is allowed.
    living = _fixed_room(
        model,
        name="living_1",
        room_type="livingRoom",
        x=20,
        y=0,
        w=20,
        h=20,
    )
    # One side can be attached while the opposite side remains open.
    side_room = _fixed_room(
        model,
        name="side_1",
        room_type="bedroom",
        x=40,
        y=20,
        w=10,
        h=20,
    )

    add_open_area_placement_constraints(model, [veranda, living, side_room])

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_open_area_placement_veranda_infeasible_when_front_and_both_sides_closed() -> None:
    model = cp_model.CpModel()

    veranda = _fixed_room(
        model,
        name="veranda_1",
        room_type="veranda",
        x=20,
        y=20,
        w=20,
        h=20,
    )
    # Closes veranda front side (bottom side in this coordinate system).
    front_block = _fixed_room(
        model,
        name="front_block",
        room_type="livingRoom",
        x=20,
        y=40,
        w=20,
        h=10,
    )
    # Closes one lateral side.
    side_a = _fixed_room(
        model,
        name="side_a",
        room_type="bedroom",
        x=40,
        y=20,
        w=10,
        h=20,
    )
    # Closes the opposite lateral side.
    side_b = _fixed_room(
        model,
        name="side_b",
        room_type="kitchen",
        x=0,
        y=20,
        w=20,
        h=20,
    )

    add_open_area_placement_constraints(model, [veranda, front_block, side_a, side_b])

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status == cp_model.INFEASIBLE


def test_open_area_placement_no_veranda_is_noop() -> None:
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
    bed = _fixed_room(
        model,
        name="bed_1",
        room_type="bedroom",
        x=40,
        y=10,
        w=20,
        h=20,
    )

    add_open_area_placement_constraints(model, [living, bed])

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

from ortools.sat.python import cp_model

from app.algorithms.fpg_rooms.constraints.hard.hard_veranda_placement import (
    add_veranda_placement_constraints,
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


def test_open_area_placement_veranda_feasible_when_front_is_y_zero_and_one_side_available() -> None:
    model = cp_model.CpModel()

    veranda = _fixed_room(
        model,
        name="veranda_1",
        room_type="veranda",
        x=5,
        y=0,
        w=10,
        h=10,
    )
    # Back attachment is allowed.
    living = _fixed_room(
        model,
        name="living_1",
        room_type="livingRoom",
        x=5,
        y=10,
        w=10,
        h=10,
    )
    # Block left expansion branch, forcing right-side verandaOutdoorSpace attachment.
    left_blocker = _fixed_room(
        model,
        name="left_blocker",
        room_type="bedroom",
        x=0,
        y=0,
        w=5,
        h=10,
    )

    add_veranda_placement_constraints(model, [veranda, living, left_blocker])

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_open_area_placement_veranda_infeasible_when_front_is_not_y_zero() -> None:
    model = cp_model.CpModel()

    veranda = _fixed_room(
        model,
        name="veranda_1",
        room_type="veranda",
        x=5,
        y=5,
        w=10,
        h=10,
    )

    add_veranda_placement_constraints(model, [veranda])

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status == cp_model.INFEASIBLE


def test_open_area_placement_veranda_feasible_when_left_attachment_branch_is_available() -> None:
    model = cp_model.CpModel()

    veranda = _fixed_room(
        model,
        name="veranda_1",
        room_type="veranda",
        x=5,
        y=0,
        w=10,
        h=10,
    )
    # Block right expansion branch, forcing left-side verandaOutdoorSpace attachment.
    right_blocker = _fixed_room(
        model,
        name="right_blocker",
        room_type="bedroom",
        x=15,
        y=0,
        w=15,
        h=10,
    )
    # Back attachment remains allowed.
    back_room = _fixed_room(
        model,
        name="back_room",
        room_type="livingRoom",
        x=5,
        y=10,
        w=10,
        h=10,
    )

    add_veranda_placement_constraints(model, [veranda, right_blocker, back_room])

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_open_area_placement_veranda_infeasible_when_both_side_expansions_are_blocked() -> None:
    model = cp_model.CpModel()

    veranda = _fixed_room(
        model,
        name="veranda_1",
        room_type="veranda",
        x=5,
        y=0,
        w=10,
        h=10,
    )
    left_blocker = _fixed_room(
        model,
        name="left_blocker",
        room_type="bedroom",
        x=0,
        y=0,
        w=5,
        h=10,
    )
    right_blocker = _fixed_room(
        model,
        name="right_blocker",
        room_type="kitchen",
        x=15,
        y=0,
        w=15,
        h=10,
    )

    add_veranda_placement_constraints(model, [veranda, left_blocker, right_blocker])

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

    add_veranda_placement_constraints(model, [living, bed])

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

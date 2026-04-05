from ortools.sat.python import cp_model

from app.algorithms.fpg_rooms.constraints.hard.kitchen_hallway_back_wall_setback import (
    add_kitchen_hallway_back_wall_setback_constraint,
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


def test_back_setback_no_kitchen_or_hallway_is_noop() -> None:
    model = cp_model.CpModel()

    living = _fixed_room(
        model,
        name="living_1",
        room_type="livingRoom",
        x=10,
        y=20,
        w=30,
        h=30,
    )
    bedroom = _fixed_room(
        model,
        name="bedroom_1",
        room_type="bedroom",
        x=50,
        y=20,
        w=30,
        h=30,
    )

    add_kitchen_hallway_back_wall_setback_constraint(
        model,
        [living, bedroom],
        floor_height=120,
        min_gap=5,
        max_gap=20,
    )

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_back_setback_only_kitchen_feasible_with_clear_zone() -> None:
    model = cp_model.CpModel()

    kitchen = _fixed_room(
        model,
        name="kitchen_1",
        room_type="kitchen",
        x=20,
        y=80,
        w=30,
        h=20,
    )

    add_kitchen_hallway_back_wall_setback_constraint(
        model,
        [kitchen],
        floor_height=120,
        min_gap=5,
        max_gap=25,
    )

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_back_setback_only_kitchen_infeasible_when_back_gap_too_small() -> None:
    model = cp_model.CpModel()

    kitchen = _fixed_room(
        model,
        name="kitchen_1",
        room_type="kitchen",
        x=20,
        y=108,
        w=30,
        h=10,
    )

    add_kitchen_hallway_back_wall_setback_constraint(
        model,
        [kitchen],
        floor_height=120,
        min_gap=5,
        max_gap=25,
    )

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status == cp_model.INFEASIBLE


def test_back_setback_only_hallway_infeasible_when_blocked_directly_behind() -> None:
    model = cp_model.CpModel()

    hallway = _fixed_room(
        model,
        name="hallway_1",
        room_type="hallway",
        x=20,
        y=80,
        w=30,
        h=20,
    )
    # This room starts immediately behind hallway back wall and overlaps x-range,
    # so it blocks the setback strip.
    blocker = _fixed_room(
        model,
        name="blocker_1",
        room_type="bedroom",
        x=25,
        y=100,
        w=20,
        h=15,
    )

    add_kitchen_hallway_back_wall_setback_constraint(
        model,
        [hallway, blocker],
        floor_height=130,
        min_gap=5,
        max_gap=30,
    )

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status == cp_model.INFEASIBLE


def test_back_setback_both_present_feasible_if_any_one_satisfies() -> None:
    model = cp_model.CpModel()

    # Kitchen has no valid back gap.
    kitchen = _fixed_room(
        model,
        name="kitchen_1",
        room_type="kitchen",
        x=10,
        y=112,
        w=20,
        h=8,
    )
    # Hallway has valid back setback and no blocker.
    hallway = _fixed_room(
        model,
        name="hallway_1",
        room_type="hallway",
        x=50,
        y=85,
        w=30,
        h=20,
    )

    add_kitchen_hallway_back_wall_setback_constraint(
        model,
        [kitchen, hallway],
        floor_height=130,
        min_gap=5,
        max_gap=30,
    )

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_back_setback_both_present_infeasible_when_neither_satisfies() -> None:
    model = cp_model.CpModel()

    kitchen = _fixed_room(
        model,
        name="kitchen_1",
        room_type="kitchen",
        x=10,
        y=112,
        w=20,
        h=8,
    )
    hallway = _fixed_room(
        model,
        name="hallway_1",
        room_type="hallway",
        x=50,
        y=113,
        w=25,
        h=7,
    )

    add_kitchen_hallway_back_wall_setback_constraint(
        model,
        [kitchen, hallway],
        floor_height=120,
        min_gap=5,
        max_gap=30,
    )

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status == cp_model.INFEASIBLE


def test_back_setback_multiple_rooms_any_one_can_satisfy() -> None:
    model = cp_model.CpModel()

    kitchen_a = _fixed_room(
        model,
        name="kitchen_a",
        room_type="kitchen",
        x=10,
        y=112,
        w=20,
        h=8,
    )
    kitchen_b = _fixed_room(
        model,
        name="kitchen_b",
        room_type="kitchen",
        x=40,
        y=90,
        w=20,
        h=20,
    )
    hallway = _fixed_room(
        model,
        name="hallway_1",
        room_type="hallway",
        x=70,
        y=112,
        w=20,
        h=8,
    )

    add_kitchen_hallway_back_wall_setback_constraint(
        model,
        [kitchen_a, kitchen_b, hallway],
        floor_height=130,
        min_gap=5,
        max_gap=30,
    )

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

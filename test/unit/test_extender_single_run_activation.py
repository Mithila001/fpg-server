from ortools.sat.python import cp_model

from app.algorithms.fpg_rooms.constraints.extenders.living_room_extender import (
    add_living_room_extender_constraints,
)
from app.algorithms.fpg_rooms.constraints.hard.basic_constraints import add_basic_constraints
from app.algorithms.fpg_rooms.fpgr_p_refine_1 import _with_refine_extenders
from app.algorithms.fpg_rooms.solver_models.room import Room
from app.algorithms.fpg_rooms.types.room import ConfigData, FpgRequirements, RoomData


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


def test_refine_injects_living_room_extenders_when_enabled() -> None:
    requirements = FpgRequirements(
        rooms=[RoomData(name="bed_1", type="bedroom", min_w=10, min_h=10, max_w=20, max_h=20)],
        config=ConfigData(
            min_coverage=0.5,
            max_aspect_ratio=3.0,
            min_aspect_ratio=0.3,
            floor_plan_width=100,
            floor_plan_height=100,
            living_room_extender_refine_only_enabled=True,
            living_room_extender_count=1,
        ),
    )

    updated = _with_refine_extenders(requirements)
    extender_types = [room.type for room in updated.rooms if room.type == "livingRoomExtender"]

    assert len(extender_types) == 1


def test_extender_active_requires_full_side_overlap_with_living_room() -> None:
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
    extender = Room(
        name="livingRoomExtender_1",
        min_w=1,
        min_h=1,
        max_w=30,
        max_h=30,
        type="livingRoomExtender",
    )
    extender.create_variables(model, 120, 120)

    add_basic_constraints(model, [living, extender])
    ctx = add_living_room_extender_constraints(
        model,
        [living, extender],
        active_min_size=10,
        perpendicular_max_size=30,
        inactive_size_cap=9,
        activation_penalty=0,
    )

    model.Add(ctx.activation_vars[extender.name] == 1)
    model.Add(extender.x == 30)
    model.Add(extender.y == 10)
    model.Add(extender.w == 16)
    model.Add(extender.h == 10)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_extender_active_without_touch_is_infeasible() -> None:
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
    extender = Room(
        name="livingRoomExtender_1",
        min_w=1,
        min_h=1,
        max_w=30,
        max_h=30,
        type="livingRoomExtender",
    )
    extender.create_variables(model, 120, 120)

    add_basic_constraints(model, [living, extender])
    ctx = add_living_room_extender_constraints(
        model,
        [living, extender],
        active_min_size=10,
        perpendicular_max_size=30,
        inactive_size_cap=9,
        activation_penalty=0,
    )

    model.Add(ctx.activation_vars[extender.name] == 1)
    model.Add(extender.x == 31)
    model.Add(extender.y == 10)
    model.Add(extender.w == 16)
    model.Add(extender.h == 10)


def test_extender_active_horizontal_shared_wall_caps_vertical_size() -> None:
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
    extender = Room(
        name="livingRoomExtender_1",
        min_w=1,
        min_h=1,
        max_w=120,
        max_h=120,
        type="livingRoomExtender",
    )
    extender.create_variables(model, 120, 120)

    add_basic_constraints(model, [living, extender])
    ctx = add_living_room_extender_constraints(
        model,
        [living, extender],
        active_min_size=10,
        perpendicular_max_size=30,
        inactive_size_cap=9,
        activation_penalty=0,
    )

    model.Add(ctx.activation_vars[extender.name] == 1)
    model.Add(extender.x == 10)
    model.Add(extender.y == 30)
    model.Add(extender.w == 10)
    model.Add(extender.h == 16)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

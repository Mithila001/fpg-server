import optuna

from app.algorithms.fpg_rooms.fpg_optuna.runner import _requirements_from_best_params, mutate_requirements
from app.algorithms.fpg_rooms.fpg_optuna.util import calculate_floor_bounds
from app.algorithms.fpg_rooms.types.room import ConfigData, FpgRequirements, RoomData


def test_mutate_requirements_uses_floor_dimension_bounds():
    base_requirements = FpgRequirements(
        rooms=[
            RoomData(name="Living Room", type="livingRoom", min_w=15, min_h=15, max_w=20, max_h=20),
            RoomData(name="Bedroom 1", type="bedroom", min_w=6, min_h=6, max_w=14, max_h=14),
        ],
        config=ConfigData(
            min_coverage=0.4,
            max_aspect_ratio=3.0,
            min_aspect_ratio=0.3,
            floor_plan_width=70,
            floor_plan_height=50,
            hallway_count=1,
        ),
        relation_constraints=[],
    )

    floor_bounds_input = {
        "min_floor_width": 40,
        "min_floor_height": 30,
        "max_floor_width": 60,
        "max_floor_height": 45,
    }

    trial = optuna.trial.FixedTrial(
        {
            "floor_plan_width": 52,
            "floor_plan_height": 41,
            "room_0_livingRoom_min_w": 15,
            "room_0_livingRoom_min_h": 15,
            "room_0_livingRoom_max_w": 20,
            "room_0_livingRoom_max_h": 20,
            "room_0_livingRoom_anchor_area": 250,
            "room_1_bedroom_target_area": 150,
            "config_min_coverage": 0.5,
            "hallway_count": 2,
        }
    )

    mutated = mutate_requirements(
        base_requirements=base_requirements,
        trial=trial,
        floor_dimension_bounds=floor_bounds_input,
    )

    assert mutated.config.floor_plan_width == 52
    assert mutated.config.floor_plan_height == 41
    assert floor_bounds_input["min_floor_width"] <= mutated.config.floor_plan_width <= floor_bounds_input["max_floor_width"]
    assert floor_bounds_input["min_floor_height"] <= mutated.config.floor_plan_height <= floor_bounds_input["max_floor_height"]

    room = mutated.rooms[0]
    assert room.type == "livingRoom"
    assert 1 <= room.min_w <= room.max_w <= mutated.config.floor_plan_width
    assert 1 <= room.min_h <= room.max_h <= mutated.config.floor_plan_height
    assert base_requirements.rooms[0].min_w <= room.min_w <= base_requirements.rooms[0].max_w
    assert base_requirements.rooms[0].min_h <= room.min_h <= base_requirements.rooms[0].max_h
    assert base_requirements.rooms[0].min_w <= room.max_w <= base_requirements.rooms[0].max_w
    assert base_requirements.rooms[0].min_h <= room.max_h <= base_requirements.rooms[0].max_h

    bedroom = mutated.rooms[1]
    assert bedroom.type == "bedroom"
    assert bedroom.min_w == bedroom.max_w
    assert bedroom.min_h == bedroom.max_h
    assert 125 <= bedroom.min_w * bedroom.min_h <= 175

    calculated_bounds = calculate_floor_bounds(
        requirements=mutated,
    )

    assert calculated_bounds.min_floor_width <= calculated_bounds.max_floor_width
    assert calculated_bounds.min_floor_height <= calculated_bounds.max_floor_height


def test_requirements_from_best_params_clamps_room_dimensions_to_base_ranges():
    base_requirements = FpgRequirements(
        rooms=[
            RoomData(name="Living Room", type="livingRoom", min_w=15, min_h=15, max_w=20, max_h=20),
            RoomData(name="Bedroom 1", type="bedroom", min_w=6, min_h=7, max_w=14, max_h=15),
        ],
        config=ConfigData(
            min_coverage=0.4,
            max_aspect_ratio=3.0,
            min_aspect_ratio=0.3,
            floor_plan_width=70,
            floor_plan_height=50,
            hallway_count=1,
        ),
        relation_constraints=[],
    )

    clamped = _requirements_from_best_params(
        base_requirements=base_requirements,
        best_params={
            "floor_plan_width": 60,
            "floor_plan_height": 45,
            "room_0_livingRoom_min_w": 15,
            "room_0_livingRoom_min_h": 15,
            "room_0_livingRoom_max_w": 20,
            "room_0_livingRoom_max_h": 20,
            "room_0_livingRoom_anchor_area": 250,
            "room_1_bedroom_target_area": 150,
            "config_min_coverage": 0.55,
            "hallway_count": 2,
        },
        floor_dimension_bounds={
            "min_floor_width": 40,
            "min_floor_height": 30,
            "max_floor_width": 60,
            "max_floor_height": 45,
        },
    )

    living_room = clamped.rooms[0]
    assert living_room.type == "livingRoom"
    assert living_room.min_w == 15
    assert living_room.min_h == 15
    assert living_room.max_w == 20
    assert living_room.max_h == 20

    room = clamped.rooms[1]
    assert room.min_w == room.max_w
    assert room.min_h == room.max_h
    assert 125 <= room.min_w * room.min_h <= 175

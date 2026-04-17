import optuna

from app.algorithms.fpg_rooms.fpg_optuna.runner import mutate_requirements
from app.algorithms.fpg_rooms.fpg_optuna.util import calculate_floor_bounds
from app.algorithms.fpg_rooms.types.room import ConfigData, FpgRequirements, RoomData


def test_mutate_requirements_uses_floor_dimension_bounds():
    base_requirements = FpgRequirements(
        rooms=[
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
            "room_0_bedroom_min_w": 7,
            "room_0_bedroom_min_h": 8,
            "room_0_bedroom_max_w": 12,
            "room_0_bedroom_max_h": 13,
            "config_min_coverage": 0.55,
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
    assert 1 <= room.min_w <= room.max_w <= mutated.config.floor_plan_width
    assert 1 <= room.min_h <= room.max_h <= mutated.config.floor_plan_height

    calculated_bounds = calculate_floor_bounds(
        requirements=mutated,
    )

    assert calculated_bounds.feasible is True
    assert calculated_bounds.min_floor_width <= calculated_bounds.max_floor_width
    assert calculated_bounds.min_floor_height <= calculated_bounds.max_floor_height

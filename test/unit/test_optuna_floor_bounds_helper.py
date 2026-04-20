from app.algorithms.fpg_rooms.fpg_optuna.util import calculate_floor_bounds
from app.algorithms.fpg_rooms.types.room import ConfigData, FpgRequirements, RoomData
from app.core.fpg_rooms.config_fpg import MIN_FLOOR_AREA_BUFFER


def _requirements(
    rooms: list[RoomData],
    hallway_count: int = 0,
    floor_width: int = 120,
    floor_height: int = 120,
) -> FpgRequirements:
    return FpgRequirements(
        rooms=rooms,
        config=ConfigData(
            min_coverage=0.5,
            max_aspect_ratio=16.0,
            min_aspect_ratio=0.0,
            floor_plan_width=floor_width,
            floor_plan_height=floor_height,
            hallway_count=hallway_count,
        ),
        relation_constraints=[],
    )


def test_calculate_floor_bounds_includes_living_room_and_hallway_area():
    requirements = _requirements(
        [
            RoomData(name="Living Room", type="livingRoom", min_w=60, min_h=60, max_w=70, max_h=70),
            RoomData(name="Bedroom", type="bedroom", min_w=20, min_h=20, max_w=20, max_h=20),
        ],
        hallway_count=2,
        floor_width=90,
        floor_height=110,
    )

    result = calculate_floor_bounds(requirements=requirements)

    assert result.feasible is True
    assert result.total_min_area == 60 * 60 + 20 * 20 + 2 * (10 * 10)
    # additional_min_area uses the configured floor-area buffer cap.
    assert result.additional_min_area == float(MIN_FLOOR_AREA_BUFFER)
    assert result.required_floor_area == result.total_min_area + float(MIN_FLOOR_AREA_BUFFER)
    assert result.min_floor_width >= 1
    assert result.min_floor_height >= 1
    assert result.min_floor_width <= 120
    assert result.min_floor_height <= 120


def test_calculate_floor_bounds_penalizes_when_area_exceeds_max_floor_area():
    requirements = _requirements(
        [
            RoomData(name="Living Room", type="livingRoom", min_w=100, min_h=100, max_w=120, max_h=120),
            RoomData(name="Bedroom", type="bedroom", min_w=10, min_h=10, max_w=10, max_h=10),
        ],
        hallway_count=0,
        floor_width=80,
        floor_height=80,
    )

    result = calculate_floor_bounds(requirements=requirements)

    assert result.feasible is False
    assert "Insufficient floor area" in result.reason


def test_calculate_floor_bounds_returns_feasible_floor_pair():
    requirements = _requirements(
        [
            RoomData(name="Living Room", type="livingRoom", min_w=60, min_h=60, max_w=70, max_h=70),
            RoomData(name="Bedroom", type="bedroom", min_w=25, min_h=25, max_w=25, max_h=25),
        ],
        hallway_count=0,
        floor_width=90,
        floor_height=110,
    )

    result = calculate_floor_bounds(requirements=requirements)

    assert result.feasible is True
    assert result.min_floor_width >= 24
    assert result.min_floor_height >= 30
    assert result.min_floor_width > 0
    assert result.min_floor_height > 0
    assert result.min_floor_width <= 90
    assert result.min_floor_height <= 110

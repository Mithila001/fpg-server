import pytest

from app.algorithms.fpg_rooms.types.room import ConfigData, FpgRequirements, RoomData
from app.algorithms.fpg_rooms.utils.generator.util_living_room import generate_living_room
from app.models.room_size_constraint import RoomSizeConstraint
from app.util.room_requirements import (
    compute_floor_plan_dimension_bounds,
    normalize_db_data_requirements,
)


def test_compute_floor_plan_bounds_success():
    requirements = FpgRequirements(
        rooms=[
            RoomData(name="Living", type="living", min_w=10, min_h=10, max_w=15, max_h=15),
            RoomData(name="Bedroom", type="bed", min_w=8, min_h=8, max_w=10, max_h=10),
        ],
        config=ConfigData(
            min_coverage=0.0,
            max_aspect_ratio=3.0,
            min_aspect_ratio=0.3,
            floor_plan_width=70,
            floor_plan_height=40,
        ),
    )

    result = compute_floor_plan_dimension_bounds(requirements)

    assert result["status"] == "OK"
    assert result["total_min_area"] == pytest.approx(10*10 + 8*8)
    assert result["normalized_aspect_ratio"] == 1
    assert result["max_floor_width"] > 0
    assert result["min_floor_width"] > 0
    assert result["min_floor_height"] > 0
    assert result["max_floor_width"] >= result["min_floor_width"]
    assert result["max_floor_height"] >= result["min_floor_height"]


def test_compute_floor_plan_bounds_portrait_aspect():
    requirements = FpgRequirements(
        rooms=[
            RoomData(name="Living", type="living", min_w=10, min_h=10, max_w=15, max_h=15),
            RoomData(name="Bedroom", type="bed", min_w=8, min_h=8, max_w=10, max_h=10),
        ],
        config=ConfigData(
            min_coverage=0.0,
            max_aspect_ratio=3.0,
            min_aspect_ratio=0.3,
            floor_plan_width=120,
            floor_plan_height=150,
        ),
    )

    result = compute_floor_plan_dimension_bounds(requirements)

    assert result["status"] == "OK"
    assert result["normalized_aspect_ratio"] == 1


def test_compute_floor_plan_bounds_invalid_room_dimensions():
    requirements = FpgRequirements(
        rooms=[RoomData(name="Bad", type="bad", min_w=-3, min_h=10, max_w=5, max_h=5)],
        config=ConfigData(
            min_coverage=0.0,
            max_aspect_ratio=3.0,
            min_aspect_ratio=0.3,
            floor_plan_width=20,
            floor_plan_height=20,
        ),
    )

    result = compute_floor_plan_dimension_bounds(requirements)

    assert result["status"] == "ERROR"


def test_compute_floor_plan_bounds_area_too_small():
    requirements = FpgRequirements(
        rooms=[RoomData(name="Big", type="big", min_w=50, min_h=50, max_w=50, max_h=50)],
        config=ConfigData(
            min_coverage=0.0,
            max_aspect_ratio=3.0,
            min_aspect_ratio=0.3,
            floor_plan_width=20,
            floor_plan_height=20,
        ),
    )

    result = compute_floor_plan_dimension_bounds(requirements)

    assert result["status"] == "ERROR"


def test_compute_floor_plan_bounds_normalization_caps_area():
    requirements = FpgRequirements(
        rooms=[
            RoomData(name="R1", type="r1", min_w=5, min_h=5, max_w=20, max_h=20),
        ],
        config=ConfigData(
            min_coverage=0.0,
            max_aspect_ratio=3.0,
            min_aspect_ratio=0.3,
            floor_plan_width=200,
            floor_plan_height=200,
        ),
    )

    result = compute_floor_plan_dimension_bounds(requirements)

    assert result["status"] == "OK"
    assert result["normalized_floor_area"] < result["floor_area"]


def test_normalize_db_data_requirements_appends_living_room():
    rooms = [
        RoomData(name="Bedroom", type="bedroom", min_w=1, min_h=1, max_w=1, max_h=1),
    ]
    constraints = [
        RoomSizeConstraint(type="bedroom", min_w=10, min_h=11, max_w=20, max_h=21),
        RoomSizeConstraint(type="livingRoom", min_w=30, min_h=31, max_w=40, max_h=41),
    ]

    normalized = normalize_db_data_requirements(rooms, constraints)

    assert [room.type for room in normalized] == ["bedroom", "livingRoom"]
    assert normalized[-1].min_w == 30
    assert normalized[-1].min_h == 31
    assert normalized[-1].max_w == 40
    assert normalized[-1].max_h == 41


def test_normalize_db_data_requirements_requires_living_room_constraint():
    rooms = [
        RoomData(name="Bedroom", type="bedroom", min_w=1, min_h=1, max_w=1, max_h=1),
    ]
    constraints = [
        RoomSizeConstraint(type="bedroom", min_w=10, min_h=11, max_w=20, max_h=21),
    ]

    with pytest.raises(ValueError, match="livingRoom has no constraint record"):
        normalize_db_data_requirements(rooms, constraints)


def test_generate_living_room_uses_requirement_bounds():
    requirements = FpgRequirements(
        rooms=[
            RoomData(name="Living Room", type="livingRoom", min_w=12, min_h=13, max_w=34, max_h=35),
        ],
        config=ConfigData(
            min_coverage=0.5,
            max_aspect_ratio=3.0,
            min_aspect_ratio=0.3,
            floor_plan_width=100,
            floor_plan_height=100,
        ),
    )

    room = generate_living_room(requirements)

    assert room.min_w == 12
    assert room.min_h == 13
    assert room.max_w == 34
    assert room.max_h == 35


def test_generate_living_room_requires_requirement_entry():
    requirements = FpgRequirements(
        rooms=[],
        config=ConfigData(
            min_coverage=0.5,
            max_aspect_ratio=3.0,
            min_aspect_ratio=0.3,
            floor_plan_width=100,
            floor_plan_height=100,
        ),
    )

    with pytest.raises(ValueError, match="LivingRoom requirement is missing"):
        generate_living_room(requirements)

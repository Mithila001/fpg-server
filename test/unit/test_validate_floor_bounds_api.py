import pytest

from app.algorithms.types.room import ConfigData, FpgRequirements, RoomData
from app.util.algorithm_manager.validate_floor_bounds import (
    validate_and_compute_floor_bounds,
)


def _requirements(rooms: list[RoomData]) -> FpgRequirements:
    return FpgRequirements(
        rooms=rooms,
        config=ConfigData(
            min_coverage=0.5,
            max_aspect_ratio=16.0,
            min_aspect_ratio=0.0,
            floor_plan_width=50,
            floor_plan_height=50,
            hallway_count=1,
        ),
        relation_constraints=[],
    )


def test_validate_floor_bounds_returns_status_message_only():
    requirements = _requirements(
        [
            RoomData(
                name="Living Room",
                type="livingRoom",
                min_w=20,
                min_h=20,
                max_w=20,
                max_h=20,
            ),
            RoomData(
                name="Bedroom", type="bedroom", min_w=10, min_h=10, max_w=20, max_h=20
            ),
        ]
    )

    result = validate_and_compute_floor_bounds(
        floor_width=50,
        floor_height=50,
        requirements=requirements,
    )

    assert result["status"] == "OK"
    assert "message" in result
    assert "min_floor_width" not in result
    assert "min_floor_height" not in result
    assert "max_floor_width" not in result
    assert "max_floor_height" not in result
    assert "floor_aspect_ratio" not in result


def test_validate_floor_bounds_rejects_insufficient_area_with_living_hallway_and_buffer():
    requirements = _requirements(
        [
            RoomData(
                name="Living Room",
                type="livingRoom",
                min_w=30,
                min_h=30,
                max_w=30,
                max_h=30,
            ),
            RoomData(
                name="Bedroom", type="bedroom", min_w=20, min_h=20, max_w=25, max_h=25
            ),
        ]
    )

    with pytest.raises(Exception, match="Insufficient floor area"):
        validate_and_compute_floor_bounds(
            floor_width=50,
            floor_height=50,
            requirements=requirements,
        )


def test_validate_floor_bounds_requires_living_room_requirement():
    requirements = _requirements(
        [
            RoomData(
                name="Bedroom", type="bedroom", min_w=10, min_h=10, max_w=20, max_h=20
            )
        ]
    )

    with pytest.raises(Exception, match="LivingRoom requirement is missing"):
        validate_and_compute_floor_bounds(
            floor_width=50,
            floor_height=50,
            requirements=requirements,
        )

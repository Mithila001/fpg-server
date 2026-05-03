import pytest

from app.algorithms.types import RoomData
from app.types.room_size_constraint import RoomSizeConstraint
from app.util.dev_use_mock_db import load_room_size_constraints
from app.util.room_requirements import normalize_db_data_requirements


def test_load_room_size_constraints_flattens_nested_structure() -> None:
    constraints = load_room_size_constraints()

    bedroom_regular = next(
        (c for c in constraints if c.type == "bedroom" and c.size == "regular"),
        None,
    )

    assert bedroom_regular is not None
    assert bedroom_regular.min_w == 30
    assert bedroom_regular.max_h == 45
    assert bedroom_regular.preset_id == "bed_r"


def test_normalize_requires_room_size() -> None:
    rooms = [
        RoomData(
            name="bedroom1",
            type="bedroom",
            min_w=1,
            min_h=1,
            max_w=2,
            max_h=2,
            size=None,
        )
    ]

    constraints = [
        RoomSizeConstraint(
            type="bedroom",
            size="regular",
            min_w=30,
            min_h=30,
            max_w=45,
            max_h=45,
        ),
        RoomSizeConstraint(
            type="livingRoom",
            size="regular",
            min_w=36,
            min_h=45,
            max_w=60,
            max_h=75,
        ),
    ]

    with pytest.raises(ValueError, match="missing required 'size'"):
        normalize_db_data_requirements(rooms, constraints)


def test_normalize_uses_type_and_size_constraints() -> None:
    rooms = [
        RoomData(
            name="bedroom1",
            type="bedroom",
            min_w=1,
            min_h=1,
            max_w=2,
            max_h=2,
            size="small",
        )
    ]

    constraints = [
        RoomSizeConstraint(
            type="bedroom",
            size="small",
            min_w=24,
            min_h=24,
            max_w=30,
            max_h=30,
        ),
        RoomSizeConstraint(
            type="bedroom",
            size="regular",
            min_w=30,
            min_h=30,
            max_w=45,
            max_h=45,
        ),
        RoomSizeConstraint(
            type="livingRoom",
            size="regular",
            min_w=36,
            min_h=45,
            max_w=60,
            max_h=75,
        ),
    ]

    normalized = normalize_db_data_requirements(rooms, constraints)

    bedroom = next(r for r in normalized if r.type == "bedroom")
    living_room = next(r for r in normalized if r.type == "livingRoom")

    assert bedroom.size == "small"
    assert bedroom.min_w == 24
    assert bedroom.max_h == 30

    assert living_room.size == "regular"
    assert living_room.min_w == 36
    assert living_room.max_h == 75

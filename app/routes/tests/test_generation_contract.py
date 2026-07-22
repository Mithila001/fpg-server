import pytest
from pydantic import ValidationError

from app.algorithms.types_new import RoomType
from app.routes.generation import FloorLimitsRequest, GenerationRoomRequest


def test_floor_limits_accept_width_and_length() -> None:
    limits = FloorLimitsRequest(max_width=120, max_length=100)

    assert limits.max_width == 120
    assert limits.max_length == 100


@pytest.mark.parametrize(
    "payload",
    (
        {"max_width": 120, "max_height": 100},
        {"max_width": 120, "max_length": 100, "max_height": 100},
    ),
)
def test_floor_limits_reject_legacy_max_height(payload: dict[str, int]) -> None:
    with pytest.raises(ValidationError):
        FloorLimitsRequest.model_validate(payload)


@pytest.mark.parametrize("room_type", tuple(RoomType))
def test_generation_room_accepts_exact_enum_value(room_type: RoomType) -> None:
    room = GenerationRoomRequest.model_validate({"room_type": room_type.value})

    assert room.room_type is room_type


@pytest.mark.parametrize(
    "room_type",
    ("Garage", "garage-room", "livingRoom", "unknown"),
)
def test_generation_room_rejects_noncanonical_value(room_type: str) -> None:
    with pytest.raises(ValidationError):
        GenerationRoomRequest.model_validate({"room_type": room_type})

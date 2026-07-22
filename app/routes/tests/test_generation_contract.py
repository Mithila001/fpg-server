import pytest
from pydantic import ValidationError

from app.routes.generation import FloorLimitsRequest


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

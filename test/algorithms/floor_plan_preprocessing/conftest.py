from __future__ import annotations

import pytest

from app.algorithms.floor_plan_preprocessing import (
    FloorLimits,
    PreprocessingInput,
    PreprocessingReferenceData,
    PreprocessingRequest,
    RequestedRoom,
    RoomSizeReference,
)


ROOM_TYPES = (
    "bedroom",
    "kitchen",
    "bathroom",
    "veranda",
    "livingRoom",
    "attachedBathroom",
    "garage",
    "diningRoom",
)


def size_reference(
    room_type: str,
    size: str = "regular",
    *,
    min_width: float = 10,
    max_width: float = 20,
    min_height: float = 10,
    max_height: float = 20,
    min_area: float = 100,
    max_area: float = 400,
) -> RoomSizeReference:
    return RoomSizeReference(
        room_type=room_type,
        size=size,
        min_width=min_width,
        max_width=max_width,
        min_height=min_height,
        max_height=max_height,
        min_area=min_area,
        max_area=max_area,
    )


@pytest.fixture
def references() -> PreprocessingReferenceData:
    return PreprocessingReferenceData(
        room_sizes=tuple(size_reference(room_type) for room_type in ROOM_TYPES)
    )


@pytest.fixture
def base_request() -> PreprocessingRequest:
    return PreprocessingRequest(
        floor_limits=FloorLimits(100, 100),
        aspect_ratio="1:1",
        rooms=(
            RequestedRoom("bedroom", "bedroom_1", requested_size="regular"),
            RequestedRoom("kitchen", "kitchen_1", requested_size="regular"),
            RequestedRoom("bathroom", "bathroom_1", requested_size="regular"),
            RequestedRoom("veranda", "veranda_1", requested_size="regular"),
        ),
    )


@pytest.fixture
def preprocessing_input(
    base_request: PreprocessingRequest, references: PreprocessingReferenceData
) -> PreprocessingInput:
    return PreprocessingInput(request=base_request, reference_data=references)

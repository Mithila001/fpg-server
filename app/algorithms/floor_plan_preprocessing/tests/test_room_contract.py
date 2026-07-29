from __future__ import annotations

from dataclasses import replace

import pytest

from app.algorithms.floor_plan_preprocessing import (
    InputValidationError,
    NormalizationError,
    PreprocessingErrorCode,
    RequestedRoom,
    prepare_generation_input,
)
from app.algorithms.types_new import RoomType


@pytest.mark.parametrize(
    ("aspect_ratio", "expected"),
    (
        ("1:2", 0.5),
        (0.75, 0.75),
        ("1:1", 1.0),
        (4 / 3, 4 / 3),
        ("2:1", 2.0),
    ),
)
def test_only_advertised_aspect_ratios_are_accepted(
    preprocessing_input,
    aspect_ratio,
    expected,
) -> None:
    value = replace(
        preprocessing_input,
        request=replace(preprocessing_input.request, aspect_ratio=aspect_ratio),
    )

    result = prepare_generation_input(value)

    assert result.report.floor_selection.aspect_ratio == pytest.approx(expected)


@pytest.mark.parametrize("aspect_ratio", ("16:9", 1.2, "bad"))
def test_unsupported_aspect_ratio_has_typed_error(
    preprocessing_input,
    aspect_ratio,
) -> None:
    value = replace(
        preprocessing_input,
        request=replace(preprocessing_input.request, aspect_ratio=aspect_ratio),
    )

    with pytest.raises(NormalizationError) as captured:
        prepare_generation_input(value)

    assert captured.value.code is PreprocessingErrorCode.INVALID_ASPECT_RATIO


def test_hallway_is_server_generated_with_requested_buffers(
    preprocessing_input,
) -> None:
    result = prepare_generation_input(preprocessing_input)
    hallways = [
        room
        for room in result.generation_spec.rooms
        if room.room_type is RoomType.HALLWAY
    ]
    non_hallway_minimum = sum(
        room.size.min_area
        for room in result.generation_spec.rooms
        if room.room_type is not RoomType.HALLWAY
    )

    assert len(hallways) == 1
    assert hallways[0].size.min_area == 300
    assert result.report.floor_selection.minimum_required_area == pytest.approx(
        non_hallway_minimum + 300 + 500
    )


def test_client_supplied_hallway_has_typed_error(preprocessing_input) -> None:
    value = replace(
        preprocessing_input,
        request=replace(
            preprocessing_input.request,
            rooms=(
                *preprocessing_input.request.rooms,
                RequestedRoom(RoomType.HALLWAY),
            ),
        ),
    )

    with pytest.raises(InputValidationError) as captured:
        prepare_generation_input(value)

    assert captured.value.code is PreprocessingErrorCode.FORBIDDEN_ROOM_TYPE


def test_missing_mandatory_room_has_structured_count_details(
    preprocessing_input,
) -> None:
    rooms = tuple(
        room
        for room in preprocessing_input.request.rooms
        if room.room_type is not RoomType.DINING_ROOM
    )
    value = replace(
        preprocessing_input,
        request=replace(preprocessing_input.request, rooms=rooms),
    )

    with pytest.raises(InputValidationError) as captured:
        prepare_generation_input(value)

    assert captured.value.code is PreprocessingErrorCode.INVALID_ROOM_COUNT
    assert captured.value.details["room_counts"] == [
        {
            "room_type": "dining_room",
            "minimum": 1,
            "maximum": 1,
            "actual": 0,
        }
    ]

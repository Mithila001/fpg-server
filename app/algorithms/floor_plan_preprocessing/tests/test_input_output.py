from dataclasses import replace

import pytest

from app.algorithms.floor_plan_preprocessing import (
    PreparedGenerationInput,
    ReferenceDataError,
    prepare_generation_input,
)
from app.algorithms.types_new import FloorPlanGenerationSpec


def test_prepare_generation_input_returns_expected_contract(
    preprocessing_input,
):
    result = prepare_generation_input(preprocessing_input)

    assert isinstance(result, PreparedGenerationInput)
    assert isinstance(
        result.generation_spec,
        FloorPlanGenerationSpec,
    )
    assert result.generation_spec.floor is not None
    assert len(result.generation_spec.rooms) > 0
    assert result.report is not None


def test_room_size_contract_contains_only_width_and_area_ranges(
    preprocessing_input,
) -> None:
    result = prepare_generation_input(preprocessing_input)
    size = result.generation_spec.rooms[0].size

    assert not hasattr(size, "min_length")
    assert not hasattr(size, "max_length")


@pytest.mark.parametrize(
    ("minimum_width", "maximum_width", "maximum_area", "message"),
    (
        (20.0, 10.0, 400.0, "Invalid width range"),
        (20.0, 30.0, 399.0, "Maximum area is below minimum width"),
    ),
)
def test_invalid_shorter_side_reference_is_rejected(
    preprocessing_input,
    minimum_width,
    maximum_width,
    maximum_area,
    message,
) -> None:
    first = preprocessing_input.reference_data.room_sizes[0]
    invalid = replace(
        first,
        min_width=minimum_width,
        max_width=maximum_width,
        max_area=maximum_area,
    )
    value = replace(
        preprocessing_input,
        reference_data=replace(
            preprocessing_input.reference_data,
            room_sizes=(invalid, *preprocessing_input.reference_data.room_sizes[1:]),
        ),
    )

    with pytest.raises(ReferenceDataError, match=message):
        prepare_generation_input(value)

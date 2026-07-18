from __future__ import annotations

import pytest

from app.algorithms.floor_plan_preprocessing import (
    BusinessRuleError,
    InputValidationError,
    NormalizationError,
    PreprocessingInput,
    PreprocessingReferenceData,
    PreprocessingRequest,
    ReferenceDataError,
    RequestedRoom,
    RoomPreparationError,
    RoomRelationReference,
    prepare_generation_input,
)
from app.algorithms.types_new import ConstraintStrength

from .conftest import size_reference


def test_rejects_duplicate_room_ids(
    base_request: PreprocessingRequest, references: PreprocessingReferenceData
) -> None:
    duplicate = RequestedRoom("bedroom", "kitchen_1", requested_size="regular")
    request = PreprocessingRequest(
        base_request.floor_limits,
        base_request.aspect_ratio,
        base_request.rooms + (duplicate,),
    )

    with pytest.raises(InputValidationError, match="Duplicate room ID"):
        prepare_generation_input(PreprocessingInput(request, references))


@pytest.mark.parametrize("ratio", ["not-a-ratio", "1:0", 0, float("inf")])
def test_rejects_malformed_aspect_ratio(
    ratio: object,
    base_request: PreprocessingRequest,
    references: PreprocessingReferenceData,
) -> None:
    invalid = PreprocessingRequest(
        base_request.floor_limits, ratio, base_request.rooms  # type: ignore[arg-type]
    )

    with pytest.raises(NormalizationError):
        prepare_generation_input(PreprocessingInput(invalid, references))


def test_rejects_out_of_range_aspect_ratio(
    base_request: PreprocessingRequest, references: PreprocessingReferenceData
) -> None:
    invalid = PreprocessingRequest(base_request.floor_limits, 2.1, base_request.rooms)

    with pytest.raises(InputValidationError, match="aspect_ratio must be between"):
        prepare_generation_input(PreprocessingInput(invalid, references))


def test_rejects_missing_mandatory_room(
    base_request: PreprocessingRequest, references: PreprocessingReferenceData
) -> None:
    rooms = tuple(room for room in base_request.rooms if room.room_type != "veranda")

    with pytest.raises(BusinessRuleError, match="veranda"):
        prepare_generation_input(
            PreprocessingInput(
                PreprocessingRequest(base_request.floor_limits, 1, rooms), references
            )
        )


def test_rejects_unsupported_required_room_size(
    base_request: PreprocessingRequest, references: PreprocessingReferenceData
) -> None:
    rooms = tuple(
        RequestedRoom(room.room_type, room.id, requested_size="enormous")
        for room in base_request.rooms
    )

    with pytest.raises(RoomPreparationError, match="enormous"):
        prepare_generation_input(
            PreprocessingInput(
                PreprocessingRequest(base_request.floor_limits, 1, rooms), references
            )
        )


def test_rejects_duplicate_reference_record(
    base_request: PreprocessingRequest, references: PreprocessingReferenceData
) -> None:
    duplicated = PreprocessingReferenceData(
        references.room_sizes + (references.room_sizes[0],)
    )

    with pytest.raises(ReferenceDataError, match="Duplicate room-size"):
        prepare_generation_input(PreprocessingInput(base_request, duplicated))


def test_rejects_inconsistent_reference_range(
    base_request: PreprocessingRequest, references: PreprocessingReferenceData
) -> None:
    invalid = size_reference("bedroom", min_width=30, max_width=20)
    data = PreprocessingReferenceData(
        (invalid,) + references.room_sizes[1:]
    )

    with pytest.raises(ReferenceDataError, match="Invalid dimension range"):
        prepare_generation_input(PreprocessingInput(base_request, data))


def test_rejects_malformed_relation_level(
    base_request: PreprocessingRequest, references: PreprocessingReferenceData
) -> None:
    relation = RoomRelationReference(
        "bedroom", ("kitchen",), "sometimes", ConstraintStrength.HARD
    )
    data = PreprocessingReferenceData(references.room_sizes, (relation,))

    with pytest.raises(ReferenceDataError, match="match policy"):
        prepare_generation_input(PreprocessingInput(base_request, data))


def test_rejects_excess_attached_bathrooms_when_configured(
    base_request: PreprocessingRequest, references: PreprocessingReferenceData
) -> None:
    from app.algorithms.floor_plan_preprocessing import (
        ExcessAttachedBathroomPolicy,
        PreprocessingPolicy,
    )

    rooms = base_request.rooms + (
        RequestedRoom("attachedBathroom", "attached_1", requested_size="regular"),
        RequestedRoom("attachedBathroom", "attached_2", requested_size="regular"),
    )
    policy = PreprocessingPolicy(
        excess_attached_bathrooms=ExcessAttachedBathroomPolicy.REJECT
    )

    with pytest.raises(BusinessRuleError, match="cannot exceed"):
        prepare_generation_input(
            PreprocessingInput(
                PreprocessingRequest(base_request.floor_limits, 1, rooms),
                references,
                policy,
            )
        )

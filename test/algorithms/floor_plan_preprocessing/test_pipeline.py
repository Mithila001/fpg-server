from __future__ import annotations

from copy import deepcopy

import pytest

from app.algorithms.floor_plan_preprocessing import (
    FloorLimits,
    FloorPreparationError,
    PreprocessingInput,
    PreprocessingReferenceData,
    PreprocessingRequest,
    RequestedRoom,
    RoomRelationReference,
    prepare_generation_input,
)
from app.algorithms.types_new import (
    ConstraintStrength,
    MatchPolicy,
    RoomType,
)

from .conftest import size_reference


def test_builds_complete_typed_specification(preprocessing_input: PreprocessingInput) -> None:
    result = prepare_generation_input(preprocessing_input)

    room_types = [room.room_type for room in result.generation_spec.rooms]
    assert RoomType.LIVING_ROOM in room_types
    assert room_types.count(RoomType.HALLWAY) == 2
    assert result.report.selected_room_size == "regular"
    assert result.generation_spec.floor.width == pytest.approx(
        result.generation_spec.floor.height
    )
    assert result.report.floor_selection.minimum_required_area == 1200


def test_normalizes_aliases_and_generates_stable_ids(
    references: PreprocessingReferenceData,
) -> None:
    request = PreprocessingRequest(
        floor_limits=FloorLimits(100, 100),
        aspect_ratio="2:1",
        rooms=(
            RequestedRoom("bedroom", requested_size="Regular"),
            RequestedRoom("kitchen", requested_size="regular"),
            RequestedRoom("bathroom", requested_size="regular"),
            RequestedRoom("veranda", requested_size="regular"),
            RequestedRoom("attachedBathroom", requested_size="regular"),
        ),
    )

    result = prepare_generation_input(PreprocessingInput(request, references))

    ids = {str(room.id) for room in result.generation_spec.rooms}
    assert "bedroom_1" in ids
    assert "attached_bathroom_1" in ids
    assert any(
        item.original == "attachedBathroom"
        and item.normalized == "attached_bathroom"
        for item in result.report.normalizations
    )
    assert result.generation_spec.floor.height == pytest.approx(
        result.generation_spec.floor.width * 2
    )


def test_does_not_mutate_any_input(preprocessing_input: PreprocessingInput) -> None:
    original = deepcopy(preprocessing_input)

    prepare_generation_input(preprocessing_input)

    assert preprocessing_input == original


def test_policy_mandatory_rooms_are_marked_required(
    base_request: PreprocessingRequest, references: PreprocessingReferenceData
) -> None:
    rooms = tuple(
        RequestedRoom(
            room.room_type,
            room.id,
            requested_size=room.requested_size,
            required=False,
        )
        for room in base_request.rooms
    )

    result = prepare_generation_input(
        PreprocessingInput(
            PreprocessingRequest(base_request.floor_limits, 1, rooms), references
        )
    )

    mandatory = {
        RoomType.BEDROOM,
        RoomType.KITCHEN,
        RoomType.BATHROOM,
        RoomType.VERANDA,
        RoomType.LIVING_ROOM,
    }
    assert all(
        room.required for room in result.generation_spec.rooms if room.room_type in mandatory
    )


def test_rejects_room_dimensions_that_do_not_fit_selected_floor(
    base_request: PreprocessingRequest, references: PreprocessingReferenceData
) -> None:
    bedroom = size_reference(
        "bedroom",
        min_width=80,
        max_width=80,
        min_height=10,
        max_height=10,
        min_area=800,
        max_area=800,
    )
    data = PreprocessingReferenceData((bedroom,) + references.room_sizes[1:])

    with pytest.raises(FloorPreparationError, match="bedroom_1"):
        prepare_generation_input(PreprocessingInput(base_request, data))


def test_removes_unsupported_optional_room(
    base_request: PreprocessingRequest, references: PreprocessingReferenceData
) -> None:
    request = PreprocessingRequest(
        base_request.floor_limits,
        base_request.aspect_ratio,
        base_request.rooms + (RequestedRoom("garage", "garage_1", required=False),),
    )
    references = PreprocessingReferenceData(
        tuple(item for item in references.room_sizes if item.room_type != "garage")
    )

    result = prepare_generation_input(PreprocessingInput(request, references))

    assert "garage_1" not in {str(room.id) for room in result.generation_spec.rooms}
    assert any(
        item.room_id == "garage_1" and item.action == "removed"
        for item in result.report.room_decisions
    )


def test_rejects_floor_that_cannot_fit_minimum_area(
    base_request: PreprocessingRequest, references: PreprocessingReferenceData
) -> None:
    request = PreprocessingRequest(FloorLimits(20, 20), 1.0, base_request.rooms)

    with pytest.raises(FloorPreparationError, match="required minimum"):
        prepare_generation_input(PreprocessingInput(request, references))


def test_majority_tie_prefers_regular(base_request: PreprocessingRequest) -> None:
    rooms = tuple(
        RequestedRoom(
            room.room_type,
            room.id,
            requested_size="small" if index < 2 else "regular",
        )
        for index, room in enumerate(base_request.rooms)
    )
    references = PreprocessingReferenceData(
        room_sizes=tuple(
            size_reference(room_type, size)
            for room_type in (
                "bedroom",
                "kitchen",
                "bathroom",
                "veranda",
                "livingRoom",
            )
            for size in ("small", "regular")
        )
    )

    result = prepare_generation_input(
        PreprocessingInput(
            PreprocessingRequest(base_request.floor_limits, 1, rooms), references
        )
    )

    assert result.report.selected_room_size == "regular"


def test_pairs_attached_bathrooms_and_expands_other_relations(
    base_request: PreprocessingRequest, references: PreprocessingReferenceData
) -> None:
    extra_rooms = (
        RequestedRoom("bedroom", "bedroom_2", requested_size="regular"),
        RequestedRoom("attachedBathroom", "attached_1", requested_size="regular"),
        RequestedRoom("attachedBathroom", "attached_2", requested_size="regular"),
        RequestedRoom("attachedBathroom", "attached_3", requested_size="regular"),
    )
    relations = (
        RoomRelationReference(
            "attachedBathroom", ("bedroom",), MatchPolicy.AND, ConstraintStrength.HARD
        ),
        RoomRelationReference(
            "bedroom",
            ("livingRoom", "hallway"),
            MatchPolicy.OR,
            ConstraintStrength.HARD,
        ),
    )
    reference_data = PreprocessingReferenceData(references.room_sizes, relations)
    result = prepare_generation_input(
        PreprocessingInput(
            PreprocessingRequest(
                FloorLimits(120, 120), 1, base_request.rooms + extra_rooms
            ),
            reference_data,
        )
    )

    relations_by_source = {
        str(relation.source_room_id): tuple(map(str, relation.target_room_ids))
        for relation in result.generation_spec.room_relations
    }
    assert relations_by_source["attached_1"] == ("bedroom_1",)
    assert relations_by_source["attached_2"] == ("bedroom_2",)
    assert "attached_3" not in relations_by_source
    assert len(relations_by_source["bedroom_1"]) == 3
    assert any(item.room_id == "attached_3" for item in result.report.room_decisions)

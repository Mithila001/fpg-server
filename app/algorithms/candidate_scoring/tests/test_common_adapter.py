from __future__ import annotations

import pytest
from typing import cast

from app.algorithms.candidate_scoring import (
    CandidateScoringInput,
    ScoringContext,
)
from app.algorithms.candidate_scoring.evaluators.common import build_evaluation_data
from app.algorithms.candidate_scoring.exceptions import ScoringInputError
from app.algorithms.types_new import FloorPlanGenerationSpec, RoomType

from .builders import build_scoring_input


def _legacy_specification(value: object) -> FloorPlanGenerationSpec:
    """Type an intentionally legacy-shaped specification used by adapter tests."""

    return cast(FloorPlanGenerationSpec, value)


def test_adapter_reads_typed_specification_and_candidate_mapping() -> None:
    data = build_evaluation_data(ScoringContext(build_scoring_input()))

    assert data.floor_width == pytest.approx(120.0)
    assert data.floor_length == pytest.approx(100.0)
    assert len(data.points) == 10
    living = next(point for point in data.points if point.room_id == "living_1")
    assert living.room_type is RoomType.LIVING_ROOM
    assert living.name == "Living Room"
    assert (living.x, living.y) == pytest.approx((60.0, 30.0))


def test_adapter_supports_enum_metadata_and_sequence_coordinates() -> None:
    scoring_input = CandidateScoringInput(
        specification=_legacy_specification({
            "width": 80,
            "length": 60,
            "rooms": [
                {"id": "living", "type": RoomType.LIVING_ROOM, "name": "Living"},
                {
                    "id": "bath",
                    "type": RoomType.ATTACHED_BATHROOM,
                    "name": "Bath",
                },
            ],
        }),
        candidate={"points": {"living": (10, 20), "bath": (30, 40)}},
    )

    data = build_evaluation_data(ScoringContext(scoring_input))

    assert [(point.room_id, point.room_type, point.x, point.y) for point in data.points] == [
        ("living", RoomType.LIVING_ROOM, 10.0, 20.0),
        ("bath", RoomType.ATTACHED_BATHROOM, 30.0, 40.0),
    ]


@pytest.mark.parametrize("room_type", ["Garage", "living-room", "livingRoom"])
def test_adapter_rejects_non_enum_room_types(room_type: str) -> None:
    scoring_input = CandidateScoringInput(
        specification=_legacy_specification(
            {
                "width": 80,
                "length": 60,
                "rooms": [{"id": "room", "type": room_type, "name": "Room"}],
            }
        ),
        candidate={"room": (10, 20)},
    )

    with pytest.raises(ScoringInputError, match="RoomType enum member"):
        build_evaluation_data(ScoringContext(scoring_input))


def test_adapter_rejects_duplicate_candidate_ids() -> None:
    scoring_input = CandidateScoringInput(
        specification=_legacy_specification(
            {"floor": {"width": 80, "length": 60}}
        ),
        candidate=[
            {
                "room_id": "same",
                "room_type": RoomType.BEDROOM,
                "x": 10,
                "y": 10,
            },
            {
                "room_id": "same",
                "room_type": RoomType.BEDROOM,
                "x": 20,
                "y": 20,
            },
        ],
    )

    with pytest.raises(ValueError, match="duplicated"):
        build_evaluation_data(ScoringContext(scoring_input))


def test_adapter_rejects_candidate_without_room_type() -> None:
    scoring_input = CandidateScoringInput(
        specification=_legacy_specification(
            {"floor": {"width": 80, "length": 60}}
        ),
        candidate={"unknown": {"x": 10, "y": 10}},
    )

    with pytest.raises(ValueError, match="has no room type"):
        build_evaluation_data(ScoringContext(scoring_input))


@pytest.mark.parametrize(
    "specification",
    [
        {"floor": {"width": 0, "length": 60}},
        {"floor": {"width": 80, "length": -1}},
        {"floor": {"width": 80}},
    ],
)
def test_adapter_rejects_invalid_floor_dimensions(specification: object) -> None:
    scoring_input = CandidateScoringInput(
        specification=_legacy_specification(specification),
        candidate={
            "bedroom": {
                "room_type": RoomType.BEDROOM,
                "x": 10,
                "y": 10,
            }
        },
    )

    with pytest.raises(ValueError):
        build_evaluation_data(ScoringContext(scoring_input))


def test_adapter_rejects_non_finite_coordinates() -> None:
    scoring_input = CandidateScoringInput(
        specification=_legacy_specification(
            {"floor": {"width": 80, "length": 60}}
        ),
        candidate={
            "bedroom": {
                "room_type": RoomType.BEDROOM,
                "x": float("nan"),
                "y": 10,
            }
        },
    )

    with pytest.raises(ValueError, match="non-finite"):
        build_evaluation_data(ScoringContext(scoring_input))


def test_adapter_accepts_multiple_hallway_hint_points() -> None:
    scoring_input = CandidateScoringInput(
        specification=_legacy_specification(
            {
                "floor": {"width": 80, "length": 60},
                "rooms": [
                    {
                        "id": "hallway",
                        "room_type": RoomType.HALLWAY,
                        "name": "Hallway",
                    }
                ],
            }
        ),
        candidate=[
            {
                "room_id": "hallway",
                "room_type": RoomType.HALLWAY,
                "hint_index": 1,
                "x": 10,
                "y": 20,
            },
            {
                "room_id": "hallway",
                "room_type": RoomType.HALLWAY,
                "hint_index": 2,
                "x": 30,
                "y": 40,
            },
        ],
    )

    data = build_evaluation_data(ScoringContext(scoring_input))

    assert [point.room_id for point in data.points] == [
        "hallway::hint:1",
        "hallway::hint:2",
    ]
    assert [point.room_type for point in data.points] == [
        RoomType.HALLWAY,
        RoomType.HALLWAY,
    ]


def test_adapter_generates_missing_hallway_hint_indexes() -> None:
    scoring_input = CandidateScoringInput(
        specification=_legacy_specification(
            {"floor": {"width": 80, "length": 60}}
        ),
        candidate=[
            {
                "room_id": "hallway",
                "room_type": RoomType.HALLWAY,
                "x": 10,
                "y": 20,
            },
            {
                "room_id": "hallway",
                "room_type": RoomType.HALLWAY,
                "x": 30,
                "y": 40,
            },
        ],
    )

    data = build_evaluation_data(ScoringContext(scoring_input))

    assert [point.room_id for point in data.points] == [
        "hallway::hint:1",
        "hallway::hint:2",
    ]


def test_adapter_rejects_duplicate_hallway_hint_indexes() -> None:
    scoring_input = CandidateScoringInput(
        specification=_legacy_specification(
            {"floor": {"width": 80, "length": 60}}
        ),
        candidate=[
            {
                "room_id": "hallway",
                "room_type": RoomType.HALLWAY,
                "hint_index": 1,
                "x": 10,
                "y": 20,
            },
            {
                "room_id": "hallway",
                "room_type": RoomType.HALLWAY,
                "hint_index": 1,
                "x": 30,
                "y": 40,
            },
        ],
    )

    with pytest.raises(ValueError, match="duplicated hint_index"):
        build_evaluation_data(ScoringContext(scoring_input))

from __future__ import annotations

import pytest

from app.algorithms.candidate_search import (
    CandidatePoint,
    CandidateSearchInput,
    CandidateSearchSettings,
    CandidateSearchTarget,
    search_candidates,
)
from Restructure_Data.floor_plan_spec import RoomId


def test_search_candidates_returns_grid_aligned_result() -> None:
    search_input = CandidateSearchInput(
        targets=(
            CandidateSearchTarget(room_id=RoomId("living_room")),
            CandidateSearchTarget(room_id=RoomId("kitchen")),
        ),
        settings=CandidateSearchSettings(
            min_x=0,
            max_x=10,
            min_y=0,
            max_y=10,
            grid_resolution=5,
            trial_count=5,
            random_seed=42,
        ),
        evaluator=lambda points: sum(point.x + point.y for point in points),
    )

    result = search_candidates(search_input)

    assert [point.room_id for point in result.points] == [
        RoomId("living_room"),
        RoomId("kitchen"),
    ]

    for point in result.points:
        assert point.x in {0.0, 5.0, 10.0}
        assert point.y in {0.0, 5.0, 10.0}

    assert result.score == search_input.evaluator(result.points)
    assert result.completed_trials == 5


def test_fixed_bounds_produce_fixed_coordinates() -> None:
    search_input = CandidateSearchInput(
        targets=(
            CandidateSearchTarget(
                room_id=RoomId("bedroom"),
            ),
        ),
        settings=CandidateSearchSettings(
            min_x=12,
            max_x=12,
            min_y=8,
            max_y=8,
            grid_resolution=2,
            trial_count=2,
            random_seed=42,
        ),
        evaluator=lambda points: 100.0,
    )

    result = search_candidates(search_input)

    assert result.points == (
        CandidatePoint(
            room_id=RoomId("bedroom"),
            x=12.0,
            y=8.0,
        ),
    )

    assert result.score == 100.0
    assert result.completed_trials == 2


def test_duplicate_room_ids_are_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="room IDs must be unique",
    ):
        CandidateSearchInput(
            targets=(
                CandidateSearchTarget(
                    room_id=RoomId("bedroom"),
                ),
                CandidateSearchTarget(
                    room_id=RoomId("bedroom"),
                ),
            ),
            settings=CandidateSearchSettings(
                min_x=0,
                max_x=10,
                min_y=0,
                max_y=10,
                grid_resolution=1,
                trial_count=2,
            ),
            evaluator=lambda points: 1.0,
        )


def test_invalid_grid_resolution_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="grid_resolution must be greater than zero",
    ):
        CandidateSearchSettings(
            min_x=0,
            max_x=10,
            min_y=0,
            max_y=10,
            grid_resolution=0,
            trial_count=2,
        )


def test_non_numeric_evaluator_result_is_rejected() -> None:
    search_input = CandidateSearchInput(
        targets=(
            CandidateSearchTarget(
                room_id=RoomId("living_room"),
            ),
        ),
        settings=CandidateSearchSettings(
            min_x=0,
            max_x=10,
            min_y=0,
            max_y=10,
            grid_resolution=5,
            trial_count=1,
            random_seed=42,
        ),
        evaluator=lambda points: "invalid",  # type: ignore[return-value]
    )

    with pytest.raises(
        TypeError,
        match="must return a numeric score",
    ):
        search_candidates(search_input)


def test_empty_targets_are_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="At least one candidate search target is required",
    ):
        CandidateSearchInput(
            targets=(),
            settings=CandidateSearchSettings(
                min_x=0,
                max_x=10,
                min_y=0,
                max_y=10,
                grid_resolution=1,
                trial_count=2,
            ),
            evaluator=lambda points: 1.0,
        )


def test_empty_room_id_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="room_id cannot be empty",
    ):
        CandidateSearchTarget(
            room_id=RoomId("   "),
        )


def test_invalid_coordinate_bounds_are_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="min_x cannot be greater than max_x",
    ):
        CandidateSearchSettings(
            min_x=20,
            max_x=10,
            min_y=0,
            max_y=10,
            grid_resolution=1,
            trial_count=2,
        )


def test_non_finite_evaluator_score_is_rejected() -> None:
    search_input = CandidateSearchInput(
        targets=(
            CandidateSearchTarget(
                room_id=RoomId("living_room"),
            ),
        ),
        settings=CandidateSearchSettings(
            min_x=0,
            max_x=10,
            min_y=0,
            max_y=10,
            grid_resolution=5,
            trial_count=1,
        ),
        evaluator=lambda points: float("inf"),
    )

    with pytest.raises(
        ValueError,
        match="non-finite score",
    ):
        search_candidates(search_input)

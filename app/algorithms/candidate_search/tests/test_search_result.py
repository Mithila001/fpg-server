from __future__ import annotations

from ..models import CandidateSearchResult
from ..optimizer import search_candidates
from .builders import (
    build_candidate_search_input,
    build_candidate_settings,
    build_recording_evaluator,
)


def test_result_contains_the_candidate_from_the_highest_scored_trial() -> None:
    trial_scores = [15.0, 42.5, -8.0, 91.0, 37.0, 66.0]
    evaluator = build_recording_evaluator(
        lambda points, trial_index: trial_scores[trial_index]
    )
    search_input = build_candidate_search_input(
        settings=build_candidate_settings(trial_count=len(trial_scores)),
        evaluator=evaluator,
    )

    result = search_candidates(search_input)

    best_trial_index = trial_scores.index(max(trial_scores))

    assert isinstance(result, CandidateSearchResult)
    assert result.score == trial_scores[best_trial_index]
    assert result.points == evaluator.calls[best_trial_index]
    assert result.completed_trials == len(trial_scores)


def test_result_preserves_target_order_and_unique_room_ids() -> None:
    search_input = build_candidate_search_input()

    result = search_candidates(search_input)

    expected_room_ids = tuple(target.room_id for target in search_input.targets)
    result_room_ids = tuple(point.room_id for point in result.points)

    assert result_room_ids == expected_room_ids
    assert len(set(result_room_ids)) == len(result_room_ids)


def test_integer_evaluator_scores_are_normalized_to_float() -> None:
    call_count = 0

    def evaluator(points: object) -> int:
        nonlocal call_count
        del points
        call_count += 1
        return call_count

    search_input = build_candidate_search_input(
        settings=build_candidate_settings(trial_count=5),
        evaluator=evaluator,
    )

    result = search_candidates(search_input)

    assert isinstance(result.score, float)
    assert result.score == 5.0

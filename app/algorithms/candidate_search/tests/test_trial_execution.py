from __future__ import annotations

from ..optimizer import search_candidates
from .builders import (
    build_candidate_search_input,
    build_candidate_settings,
    build_sequential_evaluator,
)


def test_requested_trial_count_completes_and_every_trial_is_scored() -> None:
    requested_trial_count = 17
    evaluator = build_sequential_evaluator(start=10.0, step=2.0)
    search_input = build_candidate_search_input(
        settings=build_candidate_settings(trial_count=requested_trial_count),
        evaluator=evaluator,
    )

    result = search_candidates(search_input)

    assert result.completed_trials == requested_trial_count
    assert len(evaluator.calls) == requested_trial_count
    assert len(evaluator.scores) == requested_trial_count
    assert evaluator.scores == [
        10.0 + (2.0 * trial_index)
        for trial_index in range(requested_trial_count)
    ]


def test_loop_uses_each_returned_score_and_selects_the_highest_scored_trial() -> None:
    requested_trial_count = 8
    evaluator = build_sequential_evaluator(start=-3.0, step=1.5)
    search_input = build_candidate_search_input(
        settings=build_candidate_settings(trial_count=requested_trial_count),
        evaluator=evaluator,
    )

    result = search_candidates(search_input)

    assert result.score == max(evaluator.scores)
    assert result.points == evaluator.calls[-1]


def test_evaluator_is_called_once_per_trial() -> None:
    requested_trial_count = 11
    evaluator = build_sequential_evaluator()
    search_input = build_candidate_search_input(
        settings=build_candidate_settings(trial_count=requested_trial_count),
        evaluator=evaluator,
    )

    result = search_candidates(search_input)

    assert len(evaluator.calls) == result.completed_trials
    assert len(evaluator.calls) == requested_trial_count

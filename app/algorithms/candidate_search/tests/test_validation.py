from __future__ import annotations

import math
from typing import Any

import pytest

from ..models import (
    CandidateSearchInput,
    CandidateSearchSettings,
    CandidateSearchTarget,
)
from ..optimizer import search_candidates
from .builders import (
    build_candidate_search_input,
    build_candidate_settings,
    build_candidate_target,
    build_candidate_targets,
)


def test_search_rejects_non_candidate_search_input() -> None:
    with pytest.raises(
        TypeError,
        match="search_input must be a CandidateSearchInput instance",
    ):
        search_candidates("not-search-input")  # type: ignore[arg-type]


def test_input_requires_at_least_one_target() -> None:
    with pytest.raises(ValueError, match="At least one candidate search target"):
        build_candidate_search_input(targets=())


def test_input_rejects_duplicate_room_ids() -> None:
    targets = (
        build_candidate_target("bedroom_1"),
        build_candidate_target("bedroom_1"),
    )

    with pytest.raises(ValueError, match="room IDs must be unique"):
        build_candidate_search_input(targets=targets)


def test_input_rejects_non_callable_evaluator() -> None:
    with pytest.raises(TypeError, match="evaluator must be callable"):
        CandidateSearchInput(
            targets=build_candidate_targets(),
            settings=build_candidate_settings(),
            evaluator=42,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("overrides", "expected_exception", "message"),
    [
        ({"min_x": 10.0, "max_x": 5.0}, ValueError, "min_x"),
        ({"min_y": 10.0, "max_y": 5.0}, ValueError, "min_y"),
        ({"grid_resolution": 0.0}, ValueError, "grid_resolution"),
        ({"grid_resolution": -1.0}, ValueError, "grid_resolution"),
        ({"trial_count": 0}, ValueError, "trial_count"),
        ({"trial_count": -2}, ValueError, "trial_count"),
        ({"trial_count": 2.5}, TypeError, "trial_count"),
        ({"trial_count": True}, TypeError, "trial_count"),
        ({"random_seed": 2.5}, TypeError, "random_seed"),
        ({"random_seed": False}, TypeError, "random_seed"),
        ({"min_x": math.inf}, ValueError, "min_x"),
        ({"max_y": math.nan}, ValueError, "max_y"),
    ],
)
def test_settings_reject_invalid_values(
    overrides: dict[str, Any],
    expected_exception: type[Exception],
    message: str,
) -> None:
    valid_values: dict[str, Any] = {
        "min_x": 0.0,
        "max_x": 100.0,
        "min_y": 0.0,
        "max_y": 80.0,
        "grid_resolution": 5.0,
        "trial_count": 10,
        "random_seed": 2026,
    }
    valid_values.update(overrides)

    with pytest.raises(expected_exception, match=message):
        CandidateSearchSettings(**valid_values)


@pytest.mark.parametrize(
    ("invalid_score", "expected_exception", "message"),
    [
        (True, TypeError, "numeric score, not boolean"),
        ("invalid", TypeError, "numeric score"),
        (math.inf, ValueError, "non-finite score"),
        (-math.inf, ValueError, "non-finite score"),
        (math.nan, ValueError, "non-finite score"),
    ],
)
def test_search_rejects_invalid_evaluator_scores(
    invalid_score: object,
    expected_exception: type[Exception],
    message: str,
) -> None:
    def evaluator(points: object) -> object:
        del points
        return invalid_score

    search_input = CandidateSearchInput(
        targets=build_candidate_targets(),
        settings=build_candidate_settings(trial_count=1),
        evaluator=evaluator,  # type: ignore[arg-type]
    )

    with pytest.raises(expected_exception, match=message):
        search_candidates(search_input)


def test_evaluator_exception_is_not_silently_ignored() -> None:
    class ExpectedEvaluatorError(RuntimeError):
        pass

    def evaluator(points: object) -> float:
        del points
        raise ExpectedEvaluatorError("scoring failed")

    search_input = build_candidate_search_input(evaluator=evaluator)

    with pytest.raises(ExpectedEvaluatorError, match="scoring failed"):
        search_candidates(search_input)


def test_target_room_id_is_trimmed_and_must_not_be_empty() -> None:
    target = CandidateSearchTarget(room_id="  bedroom_1  ")

    assert target.room_id == "bedroom_1"

    with pytest.raises(ValueError, match="cannot be empty"):
        CandidateSearchTarget(room_id="   ")

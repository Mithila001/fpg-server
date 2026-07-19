from __future__ import annotations

import math

from ..models import (
    CandidatePoint,
    CandidateSearchInput,
    CandidateSearchResult,
)
from ..optimizer import search_candidates


def test_candidate_search_accepts_valid_input_and_returns_valid_output(
    candidate_search_input: CandidateSearchInput,
) -> None:
    result = search_candidates(candidate_search_input)

    assert isinstance(result, CandidateSearchResult)
    assert isinstance(result.points, tuple)
    assert len(result.points) == len(candidate_search_input.targets)
    assert all(isinstance(point, CandidatePoint) for point in result.points)
    assert math.isfinite(result.score)
    assert result.completed_trials == candidate_search_input.settings.trial_count

    expected_room_ids = tuple(
        target.room_id for target in candidate_search_input.targets
    )
    actual_room_ids = tuple(point.room_id for point in result.points)

    assert actual_room_ids == expected_room_ids

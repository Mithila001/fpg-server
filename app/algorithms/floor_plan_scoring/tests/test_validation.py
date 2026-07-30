from __future__ import annotations

import pytest

from app.algorithms.floor_plan_scoring import (
    DEFAULT_SCORING_PROFILE,
    ScoringInputError,
    score_floor_plan,
)

from .builders import build_floor_plan, build_generation_spec


def test_missing_required_room_is_rejected_before_evaluation() -> None:
    floor_plan = build_floor_plan(excluded_room_ids={"bedroom_3"})
    specification = build_generation_spec()

    with pytest.raises(ScoringInputError, match="Rooms are missing"):
        score_floor_plan(floor_plan, specification, DEFAULT_SCORING_PROFILE)

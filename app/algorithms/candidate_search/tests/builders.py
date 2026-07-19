from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable

from app.algorithms.types_new import RoomId

from ..models import (
    CandidateEvaluator,
    CandidatePoint,
    CandidateSearchInput,
    CandidateSearchSettings,
    CandidateSearchTarget,
)

DEFAULT_ROOM_IDS: tuple[str, ...] = (
    "living_room_1",
    "bedroom_1",
    "kitchen_1",
)

ScoreFunction = Callable[[tuple[CandidatePoint, ...], int], float]


@dataclass(slots=True)
class RecordingEvaluator:
    """Test evaluator that records every trial candidate and returned score."""

    score_function: ScoreFunction
    calls: list[tuple[CandidatePoint, ...]] = field(default_factory=list)
    scores: list[float] = field(default_factory=list)

    def __call__(self, points: tuple[CandidatePoint, ...]) -> float:
        trial_index = len(self.calls)
        normalized_points = tuple(points)
        score = float(self.score_function(normalized_points, trial_index))

        self.calls.append(normalized_points)
        self.scores.append(score)

        return score


def build_candidate_target(
    room_id: str = "room_1",
) -> CandidateSearchTarget:
    return CandidateSearchTarget(room_id=RoomId(room_id))


def build_candidate_targets(
    room_ids: Iterable[str] = DEFAULT_ROOM_IDS,
) -> tuple[CandidateSearchTarget, ...]:
    return tuple(build_candidate_target(room_id) for room_id in room_ids)


def build_candidate_settings(
    *,
    min_x: float = 0.0,
    max_x: float = 100.0,
    min_y: float = 0.0,
    max_y: float = 80.0,
    grid_resolution: float = 5.0,
    trial_count: int = 12,
    random_seed: int | None = 2026,
) -> CandidateSearchSettings:
    return CandidateSearchSettings(
        min_x=min_x,
        max_x=max_x,
        min_y=min_y,
        max_y=max_y,
        grid_resolution=grid_resolution,
        trial_count=trial_count,
        random_seed=random_seed,
    )


def build_constant_evaluator(
    score: float = 50.0,
) -> CandidateEvaluator:
    numeric_score = float(score)

    def evaluator(points: tuple[CandidatePoint, ...]) -> float:
        del points
        return numeric_score

    return evaluator


def build_recording_evaluator(
    score_function: ScoreFunction | None = None,
) -> RecordingEvaluator:
    if score_function is None:
        def default_score_function(
            points: tuple[CandidatePoint, ...], trial_index: int
        ) -> float:
            del trial_index
            return _coordinate_score(points)

        score_function = default_score_function

    return RecordingEvaluator(score_function=score_function)


def build_sequential_evaluator(
    *,
    start: float = 1.0,
    step: float = 1.0,
) -> RecordingEvaluator:
    return build_recording_evaluator(
        lambda points, trial_index: start + (step * trial_index)
    )


def build_candidate_search_input(
    *,
    targets: tuple[CandidateSearchTarget, ...] | None = None,
    settings: CandidateSearchSettings | None = None,
    evaluator: CandidateEvaluator | None = None,
) -> CandidateSearchInput:
    return CandidateSearchInput(
        targets=targets if targets is not None else build_candidate_targets(),
        settings=settings if settings is not None else build_candidate_settings(),
        evaluator=evaluator if evaluator is not None else build_constant_evaluator(),
    )


def _coordinate_score(points: tuple[CandidatePoint, ...]) -> float:
    """Produce a deterministic score from all sampled coordinates."""

    return sum(
        ((index + 1) * point.x) + ((index + 1) * 1000.0 * point.y)
        for index, point in enumerate(points)
    )

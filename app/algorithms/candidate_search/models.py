from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, TypeAlias, Any, cast

from app.algorithms.types_new import RoomId


@dataclass(frozen=True, slots=True)
class CandidateSearchTarget:
    """
    Identifies one room for which candidate coordinates must be generated.

    Candidate Search only needs the stable room identity. It does not need the
    room type, room dimensions, display name, relations, or solver objects.
    """

    room_id: RoomId

    def __post_init__(self) -> None:
        if not isinstance(self.room_id, str):
            raise TypeError("Candidate target room_id must be a string-based RoomId.")

        cleaned_room_id = self.room_id.strip()

        if not cleaned_room_id:
            raise ValueError("Candidate target room_id cannot be empty.")

        object.__setattr__(self, "room_id", RoomId(cleaned_room_id))


@dataclass(frozen=True, slots=True)
class CandidatePoint:
    """
    A generated coordinate associated with one room.

    This is a candidate-search result point, not a final floor-plan geometry
    point. The coordinate may later be converted into a CP-SAT seed hint.
    """

    room_id: RoomId
    x: float
    y: float

    def __post_init__(self) -> None:
        if not isinstance(self.room_id, str):
            raise TypeError("Candidate point room_id must be a string-based RoomId.")

        cleaned_room_id = self.room_id.strip()

        if not cleaned_room_id:
            raise ValueError("Candidate point room_id cannot be empty.")

        object.__setattr__(self, "room_id", RoomId(cleaned_room_id))
        object.__setattr__(self, "x", _validated_finite_number("x", self.x))
        object.__setattr__(self, "y", _validated_finite_number("y", self.y))


@dataclass(frozen=True, slots=True)
class CandidateSearchSettings:
    """
    Configuration controlling the coordinate search space.

    These settings are supplied by the caller. Candidate Search does not import
    application configuration or inspect the floor-plan specification.
    """

    min_x: float
    max_x: float
    min_y: float
    max_y: float
    grid_resolution: float
    trial_count: int
    random_seed: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "min_x",
            _validated_finite_number("min_x", self.min_x),
        )
        object.__setattr__(
            self,
            "max_x",
            _validated_finite_number("max_x", self.max_x),
        )
        object.__setattr__(
            self,
            "min_y",
            _validated_finite_number("min_y", self.min_y),
        )
        object.__setattr__(
            self,
            "max_y",
            _validated_finite_number("max_y", self.max_y),
        )
        object.__setattr__(
            self,
            "grid_resolution",
            _validated_finite_number(
                "grid_resolution",
                self.grid_resolution,
            ),
        )

        if self.min_x > self.max_x:
            raise ValueError("min_x cannot be greater than max_x.")

        if self.min_y > self.max_y:
            raise ValueError("min_y cannot be greater than max_y.")

        if self.grid_resolution <= 0:
            raise ValueError("grid_resolution must be greater than zero.")

        if isinstance(self.trial_count, bool) or not isinstance(
            self.trial_count,
            int,
        ):
            raise TypeError("trial_count must be an integer.")

        if self.trial_count <= 0:
            raise ValueError("trial_count must be greater than zero.")

        if self.random_seed is not None:
            if isinstance(self.random_seed, bool) or not isinstance(
                self.random_seed,
                int,
            ):
                raise TypeError("random_seed must be an integer or None.")


CandidateEvaluator: TypeAlias = Callable[
    [tuple[CandidatePoint, ...]],
    float,
]


@dataclass(frozen=True, slots=True)
class CandidateSearchInput:
    """
    Complete input contract for one candidate-search operation.

    This is the only public input accepted by search_candidates().
    """

    targets: tuple[CandidateSearchTarget, ...]
    settings: CandidateSearchSettings
    evaluator: CandidateEvaluator

    def __post_init__(self) -> None:
        normalized_targets = tuple(self.targets)

        if not normalized_targets:
            raise ValueError("At least one candidate search target is required.")

        for target in normalized_targets:
            if not isinstance(target, CandidateSearchTarget):
                raise TypeError(
                    "Every target must be a CandidateSearchTarget instance."
                )

        room_ids = [target.room_id for target in normalized_targets]
        duplicate_room_ids = _find_duplicate_room_ids(room_ids)

        if duplicate_room_ids:
            formatted_ids = ", ".join(sorted(duplicate_room_ids))
            raise ValueError(
                f"Candidate search target room IDs must be unique: {formatted_ids}"
            )

        if not isinstance(self.settings, CandidateSearchSettings):
            raise TypeError("settings must be a CandidateSearchSettings instance.")

        if not callable(self.evaluator):
            raise TypeError("evaluator must be callable.")

        object.__setattr__(self, "targets", normalized_targets)


@dataclass(frozen=True, slots=True)
class CandidateSearchResult:
    """
    Best candidate arrangement discovered by the search.

    This is the only public output returned by search_candidates().
    """

    points: tuple[CandidatePoint, ...]
    score: float
    completed_trials: int

    def __post_init__(self) -> None:
        normalized_points = tuple(self.points)

        if not normalized_points:
            raise ValueError("Candidate search result must contain at least one point.")

        for point in normalized_points:
            if not isinstance(point, CandidatePoint):
                raise TypeError("Every result point must be a CandidatePoint instance.")

        room_ids = [point.room_id for point in normalized_points]
        duplicate_room_ids = _find_duplicate_room_ids(room_ids)

        if duplicate_room_ids:
            formatted_ids = ", ".join(sorted(duplicate_room_ids))
            raise ValueError(
                f"Candidate result room IDs must be unique: {formatted_ids}"
            )

        numeric_score = _validated_finite_number("score", self.score)

        if isinstance(self.completed_trials, bool) or not isinstance(
            self.completed_trials,
            int,
        ):
            raise TypeError("completed_trials must be an integer.")

        if self.completed_trials <= 0:
            raise ValueError("completed_trials must be greater than zero.")

        object.__setattr__(self, "points", normalized_points)
        object.__setattr__(self, "score", numeric_score)


def _validated_finite_number(
    field_name: str,
    value: object,
) -> float:
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be numeric, not boolean.")

    try:
        numeric_value = float(cast(Any, value))
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{field_name} must be numeric.") from exc

    if not math.isfinite(numeric_value):
        raise ValueError(f"{field_name} must be finite.")

    return numeric_value


def _find_duplicate_room_ids(
    room_ids: list[RoomId],
) -> set[RoomId]:
    seen: set[RoomId] = set()
    duplicates: set[RoomId] = set()

    for room_id in room_ids:
        if room_id in seen:
            duplicates.add(room_id)
        else:
            seen.add(room_id)

    return duplicates

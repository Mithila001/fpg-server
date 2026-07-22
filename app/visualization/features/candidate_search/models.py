from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class CandidatePoint:
    room_id: str
    x: int
    y: int


@dataclass(frozen=True, slots=True)
class SearchBounds:
    min_x: int
    max_x: int
    min_y: int
    max_y: int

    def __post_init__(self) -> None:
        if self.min_x >= self.max_x or self.min_y >= self.max_y:
            raise ValueError("search bounds must have positive width and length")


@dataclass(frozen=True, slots=True)
class CandidateSearchVisualization:
    trial_number: int
    score: float
    points: tuple[CandidatePoint, ...]
    bounds: SearchBounds
    grid_resolution: int = 10
    trial_count: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.grid_resolution <= 0:
            raise ValueError("grid_resolution must be greater than zero")

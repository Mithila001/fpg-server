from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, TypeAlias


@dataclass(frozen=True, slots=True)
class CoordinateTarget:
    """
    A coordinate that Optuna must generate.

    The target only needs a unique label because x and y are the values
    being searched by Optuna.
    """

    label: str

    def __post_init__(self) -> None:
        cleaned_label = self.label.strip()

        if not cleaned_label:
            raise ValueError("Coordinate target label cannot be empty.")

        object.__setattr__(self, "label", cleaned_label)


@dataclass(frozen=True, slots=True)
class Coordinate:
    """A generated coordinate belonging to a labelled target."""

    label: str
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class CoordinateOptimizationSettings:
    """
    Runtime settings supplied by the caller.

    The Optuna package does not import application configuration directly.
    """

    min_x: float
    max_x: float
    min_y: float
    max_y: float
    grid_resolution: float
    trial_count: int

    def __post_init__(self) -> None:
        numeric_values = {
            "min_x": self.min_x,
            "max_x": self.max_x,
            "min_y": self.min_y,
            "max_y": self.max_y,
            "grid_resolution": self.grid_resolution,
        }

        for field_name, value in numeric_values.items():
            if isinstance(value, bool):
                raise TypeError(f"{field_name} must be a number, not a boolean.")

            try:
                converted_value = float(value)
            except (TypeError, ValueError) as exc:
                raise TypeError(f"{field_name} must be numeric.") from exc

            if not math.isfinite(converted_value):
                raise ValueError(f"{field_name} must be finite.")

            object.__setattr__(self, field_name, converted_value)

        if self.min_x > self.max_x:
            raise ValueError("min_x cannot be greater than max_x.")

        if self.min_y > self.max_y:
            raise ValueError("min_y cannot be greater than max_y.")

        if self.grid_resolution <= 0:
            raise ValueError("grid_resolution must be greater than zero.")

        if isinstance(self.trial_count, bool) or not isinstance(self.trial_count, int):
            raise TypeError("trial_count must be an integer.")

        if self.trial_count <= 0:
            raise ValueError("trial_count must be greater than zero.")


@dataclass(frozen=True, slots=True)
class CoordinateOptimizationResult:
    """The best coordinate collection found by Optuna."""

    coordinates: tuple[Coordinate, ...]
    score: float


CoordinateEvaluator: TypeAlias = Callable[[tuple[Coordinate, ...]], float]

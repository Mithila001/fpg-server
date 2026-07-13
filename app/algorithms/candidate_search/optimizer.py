from __future__ import annotations

import math
from decimal import Decimal
from typing import Mapping, Sequence

import optuna

from .models import (
    Coordinate,
    CoordinateEvaluator,
    CoordinateOptimizationResult,
    CoordinateOptimizationSettings,
    CoordinateTarget,
)


def optimize_coordinates(
    targets: Sequence[CoordinateTarget],
    settings: CoordinateOptimizationSettings,
    evaluator: CoordinateEvaluator,
) -> CoordinateOptimizationResult:
    """
    Search for the highest-scoring coordinate arrangement.

    Flow:

        Generate coordinates
            -> pass coordinates to evaluator
            -> receive numeric score
            -> repeat for configured trial count
            -> return best coordinates and score

    The optimizer does not know what the labels represent and does not know
    anything about rooms, hallways, floor plans, scoring sections, or solvers.
    """

    validated_targets = _validate_targets(targets)

    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(),
    )

    def objective(trial: optuna.Trial) -> float:
        coordinates = _sample_coordinates(
            trial=trial,
            targets=validated_targets,
            settings=settings,
        )

        score = evaluator(coordinates)

        if isinstance(score, bool):
            raise TypeError("The coordinate evaluator must return a numeric score.")

        try:
            numeric_score = float(score)
        except (TypeError, ValueError) as exc:
            raise TypeError(
                "The coordinate evaluator must return a numeric score."
            ) from exc

        if not math.isfinite(numeric_score):
            raise ValueError("The coordinate evaluator returned a non-finite score.")

        return numeric_score

    study.optimize(
        objective,
        n_trials=settings.trial_count,
    )

    best_trial = study.best_trial

    if best_trial.value is None:
        raise RuntimeError("The best Optuna trial does not contain a score.")

    best_coordinates = _coordinates_from_parameters(
        targets=validated_targets,
        settings=settings,
        parameters=best_trial.params,
    )

    return CoordinateOptimizationResult(
        coordinates=best_coordinates,
        score=float(best_trial.value),
    )


def _validate_targets(
    targets: Sequence[CoordinateTarget],
) -> tuple[CoordinateTarget, ...]:
    validated_targets = tuple(targets)

    if not validated_targets:
        raise ValueError("At least one coordinate target is required.")

    labels = [target.label for target in validated_targets]

    duplicate_labels = {label for label in labels if labels.count(label) > 1}

    if duplicate_labels:
        duplicates = ", ".join(sorted(duplicate_labels))
        raise ValueError(f"Coordinate target labels must be unique: {duplicates}")

    return validated_targets


def _sample_coordinates(
    trial: optuna.Trial,
    targets: tuple[CoordinateTarget, ...],
    settings: CoordinateOptimizationSettings,
) -> tuple[Coordinate, ...]:
    max_x_index = _maximum_grid_index(
        minimum=settings.min_x,
        maximum=settings.max_x,
        resolution=settings.grid_resolution,
    )

    max_y_index = _maximum_grid_index(
        minimum=settings.min_y,
        maximum=settings.max_y,
        resolution=settings.grid_resolution,
    )

    coordinates: list[Coordinate] = []

    for target_index, target in enumerate(targets):
        x_index = trial.suggest_int(
            name=_x_parameter_name(target_index),
            low=0,
            high=max_x_index,
        )

        y_index = trial.suggest_int(
            name=_y_parameter_name(target_index),
            low=0,
            high=max_y_index,
        )

        coordinates.append(
            Coordinate(
                label=target.label,
                x=_grid_value(
                    minimum=settings.min_x,
                    index=x_index,
                    resolution=settings.grid_resolution,
                ),
                y=_grid_value(
                    minimum=settings.min_y,
                    index=y_index,
                    resolution=settings.grid_resolution,
                ),
            )
        )

    return tuple(coordinates)


def _coordinates_from_parameters(
    targets: tuple[CoordinateTarget, ...],
    settings: CoordinateOptimizationSettings,
    parameters: Mapping[str, int | float],
) -> tuple[Coordinate, ...]:
    coordinates: list[Coordinate] = []

    for target_index, target in enumerate(targets):
        x_parameter = _x_parameter_name(target_index)
        y_parameter = _y_parameter_name(target_index)

        if x_parameter not in parameters or y_parameter not in parameters:
            raise RuntimeError(
                f"Best trial is missing parameters for target '{target.label}'."
            )

        coordinates.append(
            Coordinate(
                label=target.label,
                x=_grid_value(
                    minimum=settings.min_x,
                    index=int(parameters[x_parameter]),
                    resolution=settings.grid_resolution,
                ),
                y=_grid_value(
                    minimum=settings.min_y,
                    index=int(parameters[y_parameter]),
                    resolution=settings.grid_resolution,
                ),
            )
        )

    return tuple(coordinates)


def _maximum_grid_index(
    minimum: float,
    maximum: float,
    resolution: float,
) -> int:
    minimum_decimal = Decimal(str(minimum))
    maximum_decimal = Decimal(str(maximum))
    resolution_decimal = Decimal(str(resolution))

    available_distance = maximum_decimal - minimum_decimal

    return int(available_distance // resolution_decimal)


def _grid_value(
    minimum: float,
    index: int,
    resolution: float,
) -> float:
    minimum_decimal = Decimal(str(minimum))
    resolution_decimal = Decimal(str(resolution))

    value = minimum_decimal + Decimal(index) * resolution_decimal

    return float(value)


def _x_parameter_name(target_index: int) -> str:
    return f"coordinate_{target_index}_x_index"


def _y_parameter_name(target_index: int) -> str:
    return f"coordinate_{target_index}_y_index"

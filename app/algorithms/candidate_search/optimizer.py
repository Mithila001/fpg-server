from __future__ import annotations

import math
from decimal import Decimal
from typing import Any, Mapping, cast

import optuna

from app.visualization.api import (
    CandidatePoint as VisualizationCandidatePoint,
)
from app.visualization.api import (
    CandidateSearchVisualization,
    SearchBounds,
    render_candidate_search,
)

from .models import (
    CandidatePoint,
    CandidateSearchInput,
    CandidateSearchResult,
    CandidateSearchSettings,
    CandidateSearchTarget,
)


def search_candidates(
    search_input: CandidateSearchInput,
) -> CandidateSearchResult:
    """
    Search for the highest-scoring candidate coordinate arrangement.

    Public contract:

        CandidateSearchInput
            -> search_candidates()
            -> CandidateSearchResult

    Candidate Search does not know how candidate points are interpreted.
    Architectural and floor-plan scoring remains the evaluator's responsibility.
    """

    if not isinstance(search_input, CandidateSearchInput):
        raise TypeError("search_input must be a CandidateSearchInput instance.")

    sampler = optuna.samplers.TPESampler(
        seed=search_input.settings.random_seed,
    )

    study = optuna.create_study(
        direction="maximize",
        sampler=sampler,
    )

    def objective(trial: optuna.Trial) -> float:
        points = _sample_candidate_points(
            trial=trial,
            targets=search_input.targets,
            settings=search_input.settings,
        )

        ##  Ideal Place for Visualizer
        score = _validate_evaluator_score(search_input.evaluator(points))

        # Candidate Search visualization
        render_candidate_search(
            CandidateSearchVisualization(
                trial_number=trial.number,
                score=score,
                points=tuple(
                    VisualizationCandidatePoint(
                        room_id=str(point.room_id),
                        x=int(point.x),
                        y=int(point.y),
                    )
                    for point in points
                ),
                bounds=SearchBounds(
                    min_x=int(search_input.settings.min_x),
                    max_x=int(search_input.settings.max_x),
                    min_y=int(search_input.settings.min_y),
                    max_y=int(search_input.settings.max_y),
                ),
                grid_resolution=int(search_input.settings.grid_resolution),
                trial_count=search_input.settings.trial_count,
            )
        )

        return score

    study.optimize(
        objective,
        n_trials=search_input.settings.trial_count,
    )

    if not study.trials:
        raise RuntimeError("Candidate search completed without any trials.")

    best_trial = study.best_trial

    if best_trial.value is None:
        raise RuntimeError("The best Optuna trial does not contain a score.")

    best_points = _points_from_trial_parameters(
        targets=search_input.targets,
        settings=search_input.settings,
        parameters=best_trial.params,
    )

    completed_trials = sum(
        trial.state == optuna.trial.TrialState.COMPLETE for trial in study.trials
    )

    if completed_trials <= 0:
        raise RuntimeError("Candidate search did not complete any successful trials.")

    return CandidateSearchResult(
        points=best_points,
        score=float(best_trial.value),
        completed_trials=completed_trials,
    )


def _sample_candidate_points(
    trial: optuna.Trial,
    targets: tuple[CandidateSearchTarget, ...],
    settings: CandidateSearchSettings,
) -> tuple[CandidatePoint, ...]:
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

    points: list[CandidatePoint] = []

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

        points.append(
            CandidatePoint(
                room_id=target.room_id,
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

    return tuple(points)


def _points_from_trial_parameters(
    targets: tuple[CandidateSearchTarget, ...],
    settings: CandidateSearchSettings,
    parameters: Mapping[str, int | float],
) -> tuple[CandidatePoint, ...]:
    points: list[CandidatePoint] = []

    for target_index, target in enumerate(targets):
        x_parameter_name = _x_parameter_name(target_index)
        y_parameter_name = _y_parameter_name(target_index)

        if x_parameter_name not in parameters:
            raise RuntimeError(
                f"Best trial is missing the X parameter for room '{target.room_id}'."
            )

        if y_parameter_name not in parameters:
            raise RuntimeError(
                f"Best trial is missing the Y parameter for room '{target.room_id}'."
            )

        x_index = _validated_parameter_index(
            parameter_name=x_parameter_name,
            value=parameters[x_parameter_name],
        )

        y_index = _validated_parameter_index(
            parameter_name=y_parameter_name,
            value=parameters[y_parameter_name],
        )

        points.append(
            CandidatePoint(
                room_id=target.room_id,
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

    return tuple(points)


def _validate_evaluator_score(value: object) -> float:
    if isinstance(value, bool):
        raise TypeError("Candidate evaluator must return a numeric score, not boolean.")

    try:
        numeric_score = float(cast(Any, value))
    except (TypeError, ValueError) as exc:
        raise TypeError("Candidate evaluator must return a numeric score.") from exc

    if not math.isfinite(numeric_score):
        raise ValueError("Candidate evaluator returned a non-finite score.")

    return numeric_score


def _validated_parameter_index(
    parameter_name: str,
    value: int | float,
) -> int:
    if isinstance(value, bool):
        raise RuntimeError(
            f"Trial parameter '{parameter_name}' contains a boolean value."
        )

    numeric_value = float(value)

    if not numeric_value.is_integer():
        raise RuntimeError(
            f"Trial parameter '{parameter_name}' is not an integer index."
        )

    index = int(numeric_value)

    if index < 0:
        raise RuntimeError(
            f"Trial parameter '{parameter_name}' contains a negative index."
        )

    return index


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
    return f"candidate_{target_index}_x_index"


def _y_parameter_name(target_index: int) -> str:
    return f"candidate_{target_index}_y_index"

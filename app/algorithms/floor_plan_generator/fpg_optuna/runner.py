from __future__ import annotations

import copy
from typing import Callable

import optuna

from app.algorithms.floor_plan_generator.types.room import (
    ConfigData,
    FpgRequirements,
    RoomData,
)

from .types import FpgEvaluationResult, OptunaOptimizationResult

EVALUATION_FN = Callable[[FpgRequirements, bool], FpgEvaluationResult]


def _trial_param_key(room: RoomData, index: int, suffix: str) -> str:
    return f"room_{index}_{room.type}_{suffix}"


def _tune_room_dimension(
    trial: optuna.Trial,
    floor_w: int,
    floor_h: int,
    room: RoomData,
    index: int,
) -> RoomData:
    base_max_w = max(1, min(int(room.max_w), floor_w))
    base_max_h = max(1, min(int(room.max_h), floor_h))
    base_min_w = max(1, min(int(room.min_w), base_max_w))
    base_min_h = max(1, min(int(room.min_h), base_max_h))

    min_w_low = max(1, base_min_w - 5)
    min_w_high = min(base_max_w, base_min_w + 5)
    min_w = trial.suggest_int(_trial_param_key(room, index, "min_w"), min_w_low, min_w_high)

    min_h_low = max(1, base_min_h - 5)
    min_h_high = min(base_max_h, base_min_h + 5)
    min_h = trial.suggest_int(_trial_param_key(room, index, "min_h"), min_h_low, min_h_high)

    max_w_low = max(min_w, max(1, base_max_w - 10))
    max_w_high = max(max_w_low, min(floor_w, base_max_w + 10))
    max_w = trial.suggest_int(_trial_param_key(room, index, "max_w"), max_w_low, max_w_high)

    max_h_low = max(min_h, max(1, base_max_h - 10))
    max_h_high = max(max_h_low, min(floor_h, base_max_h + 10))
    max_h = trial.suggest_int(_trial_param_key(room, index, "max_h"), max_h_low, max_h_high)

    return RoomData(
        name=room.name,
        type=room.type,
        min_w=min_w,
        min_h=min_h,
        max_w=max_w,
        max_h=max_h,
    )


def mutate_requirements(base_requirements: FpgRequirements, trial: optuna.Trial) -> FpgRequirements:
    floor_w = int(base_requirements.config.floor_plan_width)
    floor_h = int(base_requirements.config.floor_plan_height)

    tuned_rooms: list[RoomData] = []
    for idx, room in enumerate(base_requirements.rooms):
        tuned_rooms.append(_tune_room_dimension(trial, floor_w, floor_h, room, idx))

    tuned_config = ConfigData(
        min_coverage=trial.suggest_float("config_min_coverage", 0.30, 0.90, step=0.05),
        hallway_count=trial.suggest_int("hallway_count", 0, 3),
        max_aspect_ratio=base_requirements.config.max_aspect_ratio,
        min_aspect_ratio=base_requirements.config.min_aspect_ratio,
        floor_plan_width=base_requirements.config.floor_plan_width,
        floor_plan_height=base_requirements.config.floor_plan_height,
    )

    return FpgRequirements(
        rooms=tuned_rooms,
        config=tuned_config,
        relation_constraints=copy.deepcopy(base_requirements.relation_constraints),
    )


def _relation_constraints_are_resolvable(requirements: FpgRequirements) -> tuple[bool, str]:
    available_types = {room.type for room in requirements.rooms}
    # mandatory system rooms are injected by FloorPlanGenerator.
    available_types.update({"livingRoom", "hallway"})

    for item in requirements.relation_constraints:
        room_type = getattr(item, "room_type", None)
        related_room = getattr(item, "related_room", None)

        if not room_type or room_type not in available_types:
            return False, f"Unknown room_type in relation constraints: {room_type}"

        for related_type in related_room or []:
            if related_type not in available_types:
                return False, f"Unknown related_room type in relation constraints: {related_type}"

    return True, ""


def _bounds_are_valid(requirements: FpgRequirements) -> tuple[bool, str]:
    floor_w = int(requirements.config.floor_plan_width)
    floor_h = int(requirements.config.floor_plan_height)

    for room in requirements.rooms:
        if room.min_w < 1 or room.min_h < 1:
            return False, f"Invalid min dimensions for {room.type}"
        if room.min_w > room.max_w or room.min_h > room.max_h:
            return False, f"Invalid min/max ordering for {room.type}"
        if room.max_w > floor_w or room.max_h > floor_h:
            return False, f"Room max dimension exceeds floor bounds for {room.type}"

    coverage = float(requirements.config.min_coverage)
    if coverage <= 0.0 or coverage > 1.0:
        return False, "min_coverage must be in (0, 1]"

    return True, ""


def _precheck(requirements: FpgRequirements) -> tuple[bool, str]:
    valid, reason = _bounds_are_valid(requirements)
    if not valid:
        return False, reason

    valid, reason = _relation_constraints_are_resolvable(requirements)
    if not valid:
        return False, reason

    return True, ""


def _requirements_from_best_params(
    base_requirements: FpgRequirements,
    best_params: dict[str, float | int],
) -> FpgRequirements:
    floor_w = int(base_requirements.config.floor_plan_width)
    floor_h = int(base_requirements.config.floor_plan_height)

    tuned_rooms: list[RoomData] = []
    for idx, room in enumerate(base_requirements.rooms):
        base_max_w = max(1, min(int(room.max_w), floor_w))
        base_max_h = max(1, min(int(room.max_h), floor_h))
        base_min_w = max(1, min(int(room.min_w), base_max_w))
        base_min_h = max(1, min(int(room.min_h), base_max_h))

        min_w = int(best_params.get(_trial_param_key(room, idx, "min_w"), base_min_w))
        min_h = int(best_params.get(_trial_param_key(room, idx, "min_h"), base_min_h))
        max_w = int(best_params.get(_trial_param_key(room, idx, "max_w"), base_max_w))
        max_h = int(best_params.get(_trial_param_key(room, idx, "max_h"), base_max_h))

        min_w = max(1, min(min_w, floor_w))
        min_h = max(1, min(min_h, floor_h))
        max_w = max(min_w, min(max_w, floor_w))
        max_h = max(min_h, min(max_h, floor_h))

        tuned_rooms.append(
            RoomData(
                name=room.name,
                type=room.type,
                min_w=min_w,
                min_h=min_h,
                max_w=max_w,
                max_h=max_h,
            )
        )

    coverage = float(
        best_params.get("config_min_coverage", float(base_requirements.config.min_coverage))
    )
    coverage = min(1.0, max(0.01, coverage))
    base_hallway_count = int(getattr(base_requirements.config, "hallway_count", 1))
    hallway_count = int(best_params.get("hallway_count", base_hallway_count))
    hallway_count = max(0, min(3, hallway_count))

    tuned_config = ConfigData(
        min_coverage=coverage,
        hallway_count=hallway_count,
        max_aspect_ratio=base_requirements.config.max_aspect_ratio,
        min_aspect_ratio=base_requirements.config.min_aspect_ratio,
        floor_plan_width=base_requirements.config.floor_plan_width,
        floor_plan_height=base_requirements.config.floor_plan_height,
    )

    return FpgRequirements(
        rooms=tuned_rooms,
        config=tuned_config,
        relation_constraints=copy.deepcopy(base_requirements.relation_constraints),
    )


def run_optuna_optimization(
    base_requirements: FpgRequirements,
    evaluator: EVALUATION_FN,
    n_trials: int = 50,
    study_name: str = "fpg_layout_optimization",
    storage: str | None = None,
) -> OptunaOptimizationResult:
    """Run Optuna optimization for floor-plan requirements."""

    best_run_by_trial: dict[int, FpgEvaluationResult] = {}

    def objective(trial: optuna.Trial) -> float:
        trial_requirements = mutate_requirements(base_requirements, trial)

        ok, reason = _precheck(trial_requirements)
        if not ok:
            trial.set_user_attr("status", "precheck_failed")
            trial.set_user_attr("reason", reason)
            trial.set_user_attr("valid", False)
            return 0.0

        result = evaluator(trial_requirements, False)
        best_run_by_trial[trial.number] = result

        trial.set_user_attr("status", result.status)
        trial.set_user_attr("message", result.message)
        trial.set_user_attr("solved", result.solved)

        if not result.solved or result.score_report is None:
            trial.set_user_attr("valid", False)
            return 0.0

        trial.set_user_attr("valid", result.score_report.valid)
        if not result.score_report.valid:
            trial.set_user_attr("hard_violations", result.score_report.hard_violations)
            return 0.0

        return float(result.score_report.total_score)

    sampler = optuna.samplers.TPESampler()

    study = optuna.create_study(
        direction="maximize",
        sampler=sampler,
        study_name=study_name,
        storage=storage,
        load_if_exists=True,
    )

    study.optimize(objective, n_trials=n_trials)

    failed_trials = 0
    for trial in study.trials[-n_trials:]:
        if float(trial.value or 0.0) <= 0.0:
            failed_trials += 1

    best_run = best_run_by_trial.get(study.best_trial.number)
    if best_run is None:
        # The best trial can come from a previous run when load_if_exists=True.
        # Rebuild and evaluate it so callers always get coordinates.
        best_requirements = _requirements_from_best_params(
            base_requirements,
            dict(study.best_params),
        )
        ok, reason = _precheck(best_requirements)
        if ok:
            best_run = evaluator(best_requirements, False)
        else:
            best_run = FpgEvaluationResult(
                solved=False,
                solution=[],
                score_report=None,
                status="precheck_failed",
                message=reason,
            )

    return OptunaOptimizationResult(
        study_name=study.study_name,
        best_value=float(study.best_value),
        best_trial_number=int(study.best_trial.number),
        best_params=dict(study.best_params),
        completed_trials=len(study.trials),
        failed_trials=failed_trials,
        best_run=best_run,
    )

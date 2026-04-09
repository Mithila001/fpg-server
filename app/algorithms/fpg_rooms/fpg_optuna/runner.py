from __future__ import annotations

import copy
import time
from typing import Callable

import optuna

from app.algorithms.fpg_rooms.types.room import (
    ConfigData,
    FpgRequirements,
    RoomData,
)
from app.core.fpg_rooms.config_fpg import (
    TRIAL_EARLY_STOP_SCORE_THRESHOLD,
    TRIAL_OPTIMIZATION_TIMEOUT_SECONDS,
)
from app.core.fpg_rooms.config_optuna import (
    OPTUNA_DEFAULT_STUDY_NAME,
    OPTUNA_DEFAULT_TRIALS,
    OPTUNA_DIMENSION_MAX_JITTER,
    OPTUNA_DIMENSION_MIN_JITTER,
    OPTUNA_ENVELOPE_APPLY_SIDES_DEFAULT,
    OPTUNA_ENVELOPE_ENABLED_DEFAULT,
    OPTUNA_ENVELOPE_EXCLUDE_TYPES_DEFAULT,
    OPTUNA_ENVELOPE_MAX_GAP_DEFAULT,
    OPTUNA_ENVELOPE_MIN_GAP_DEFAULT,
    OPTUNA_HALLWAY_COUNT_MAX,
    OPTUNA_HALLWAY_COUNT_MIN,
    OPTUNA_MIN_COVERAGE_FLOOR,
    OPTUNA_MIN_COVERAGE_HIGH,
    OPTUNA_MIN_COVERAGE_LOW,
    OPTUNA_MIN_COVERAGE_STEP,
    OPTUNA_PARAM_KEY_HALLWAY_COUNT,
    OPTUNA_PARAM_KEY_MIN_COVERAGE,
)
from app.util.tracking import get_tracking_context

from .exceptions import TrialTimeoutError
from .types import FpgEvaluationResult, OptunaOptimizationResult

EVALUATION_FN = Callable[[FpgRequirements, bool], FpgEvaluationResult]
FLOOR_DIMENSION_BOUNDS = dict[str, int]

OPTUNA_PARAM_KEY_FLOOR_PLAN_WIDTH = "floor_plan_width"
OPTUNA_PARAM_KEY_FLOOR_PLAN_HEIGHT = "floor_plan_height"


class OptunaOptimizationController:
    """Controller to manage trial optimization early stopping and timeout logic."""

    def __init__(self, timeout_seconds: int = TRIAL_OPTIMIZATION_TIMEOUT_SECONDS, score_threshold: float = TRIAL_EARLY_STOP_SCORE_THRESHOLD):
        """
        Initialize the optimization controller.

        Args:
            timeout_seconds: Maximum time allowed for all trials (seconds)
            score_threshold: Score threshold for early stopping (0-100)
        """
        self.timeout_seconds = timeout_seconds
        self.score_threshold = score_threshold
        self.start_time = time.time()
        self.best_score: float | None = None
        self.feasible_found = False

    def get_elapsed_time(self) -> float:
        """Get elapsed time since controller creation (seconds)."""
        return time.time() - self.start_time

    def check_timeout_and_raise(self) -> None:
        """Raise TrialTimeoutError if timeout exceeded."""
        elapsed = self.get_elapsed_time()
        if elapsed > self.timeout_seconds:
            raise TrialTimeoutError(elapsed_time=elapsed, timeout_seconds=self.timeout_seconds)

    def should_stop_optimization(self, score: float) -> bool:
        """
        Check if optimization should stop (early stopping condition).

        Args:
            score: The score from the current trial

        Returns:
            True if optimization should stop, False otherwise
        """
        # Update best score
        if self.best_score is None or score > self.best_score:
            self.best_score = score

        # Check if score exceeds threshold
        if score >= self.score_threshold:
            self.feasible_found = True
            return True

        # Check if timeout exceeded
        if self.get_elapsed_time() > self.timeout_seconds:
            # Don't raise here; let caller decide how to handle
            return False

        return False


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

    min_w_low = max(1, base_min_w - OPTUNA_DIMENSION_MIN_JITTER)
    min_w_high = min(base_max_w, base_min_w + OPTUNA_DIMENSION_MIN_JITTER)
    min_w = trial.suggest_int(_trial_param_key(room, index, "min_w"), min_w_low, min_w_high)

    min_h_low = max(1, base_min_h - OPTUNA_DIMENSION_MIN_JITTER)
    min_h_high = min(base_max_h, base_min_h + OPTUNA_DIMENSION_MIN_JITTER)
    min_h = trial.suggest_int(_trial_param_key(room, index, "min_h"), min_h_low, min_h_high)

    max_w_low = max(min_w, max(1, base_max_w - OPTUNA_DIMENSION_MAX_JITTER))
    max_w_high = max(max_w_low, min(floor_w, base_max_w + OPTUNA_DIMENSION_MAX_JITTER))
    max_w = trial.suggest_int(_trial_param_key(room, index, "max_w"), max_w_low, max_w_high)

    max_h_low = max(min_h, max(1, base_max_h - OPTUNA_DIMENSION_MAX_JITTER))
    max_h_high = max(max_h_low, min(floor_h, base_max_h + OPTUNA_DIMENSION_MAX_JITTER))
    max_h = trial.suggest_int(_trial_param_key(room, index, "max_h"), max_h_low, max_h_high)

    return RoomData(
        name=room.name,
        type=room.type,
        min_w=min_w,
        min_h=min_h,
        max_w=max_w,
        max_h=max_h,
    )


def _resolve_floor_dimension_bounds(
    base_requirements: FpgRequirements,
    floor_dimension_bounds: FLOOR_DIMENSION_BOUNDS | None,
) -> tuple[int, int, int, int]:
    base_floor_w = max(1, int(base_requirements.config.floor_plan_width))
    base_floor_h = max(1, int(base_requirements.config.floor_plan_height))

    if floor_dimension_bounds is None:
        return base_floor_w, base_floor_h, base_floor_w, base_floor_h

    min_floor_w = int(floor_dimension_bounds.get("min_floor_width", base_floor_w))
    min_floor_h = int(floor_dimension_bounds.get("min_floor_height", base_floor_h))
    max_floor_w = int(floor_dimension_bounds.get("max_floor_width", base_floor_w))
    max_floor_h = int(floor_dimension_bounds.get("max_floor_height", base_floor_h))

    min_floor_w = max(1, min_floor_w)
    min_floor_h = max(1, min_floor_h)
    max_floor_w = max(min_floor_w, max_floor_w)
    max_floor_h = max(min_floor_h, max_floor_h)

    return min_floor_w, min_floor_h, max_floor_w, max_floor_h


def mutate_requirements(
    base_requirements: FpgRequirements,
    trial: optuna.Trial,
    floor_dimension_bounds: FLOOR_DIMENSION_BOUNDS | None = None,
) -> FpgRequirements:
    min_floor_w, min_floor_h, max_floor_w, max_floor_h = _resolve_floor_dimension_bounds(
        base_requirements,
        floor_dimension_bounds,
    )

    floor_w = trial.suggest_int(
        OPTUNA_PARAM_KEY_FLOOR_PLAN_WIDTH,
        min_floor_w,
        max_floor_w,
    )
    floor_h = trial.suggest_int(
        OPTUNA_PARAM_KEY_FLOOR_PLAN_HEIGHT,
        min_floor_h,
        max_floor_h,
    )

    tuned_rooms: list[RoomData] = []
    for idx, room in enumerate(base_requirements.rooms):
        tuned_rooms.append(_tune_room_dimension(trial, floor_w, floor_h, room, idx))

    tuned_config = ConfigData(
        min_coverage=trial.suggest_float(
            OPTUNA_PARAM_KEY_MIN_COVERAGE,
            OPTUNA_MIN_COVERAGE_LOW,
            OPTUNA_MIN_COVERAGE_HIGH,
            step=OPTUNA_MIN_COVERAGE_STEP,
        ),
        hallway_count=trial.suggest_int(
            OPTUNA_PARAM_KEY_HALLWAY_COUNT,
            OPTUNA_HALLWAY_COUNT_MIN,
            OPTUNA_HALLWAY_COUNT_MAX,
        ),
        max_aspect_ratio=base_requirements.config.max_aspect_ratio,
        min_aspect_ratio=base_requirements.config.min_aspect_ratio,
        floor_plan_width=floor_w,
        floor_plan_height=floor_h,
        envelope_enabled=bool(
            getattr(
                base_requirements.config,
                "envelope_enabled",
                OPTUNA_ENVELOPE_ENABLED_DEFAULT,
            )
        ),
        envelope_min_gap=int(
            getattr(
                base_requirements.config,
                "envelope_min_gap",
                OPTUNA_ENVELOPE_MIN_GAP_DEFAULT,
            )
        ),
        envelope_max_gap=int(
            getattr(
                base_requirements.config,
                "envelope_max_gap",
                OPTUNA_ENVELOPE_MAX_GAP_DEFAULT,
            )
        ),
        envelope_exclude_types=list(
            getattr(
                base_requirements.config,
                "envelope_exclude_types",
                OPTUNA_ENVELOPE_EXCLUDE_TYPES_DEFAULT,
            )
        ),
        envelope_apply_sides=list(
            getattr(
                base_requirements.config,
                "envelope_apply_sides",
                OPTUNA_ENVELOPE_APPLY_SIDES_DEFAULT,
            )
        ),
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

    if floor_w < 1 or floor_h < 1:
        return False, "floor_plan_width and floor_plan_height must be positive"

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
    floor_dimension_bounds: FLOOR_DIMENSION_BOUNDS | None = None,
) -> FpgRequirements:
    min_floor_w, min_floor_h, max_floor_w, max_floor_h = _resolve_floor_dimension_bounds(
        base_requirements,
        floor_dimension_bounds,
    )

    floor_w = int(best_params.get(OPTUNA_PARAM_KEY_FLOOR_PLAN_WIDTH, min_floor_w))
    floor_h = int(best_params.get(OPTUNA_PARAM_KEY_FLOOR_PLAN_HEIGHT, min_floor_h))
    floor_w = max(min_floor_w, min(max_floor_w, floor_w))
    floor_h = max(min_floor_h, min(max_floor_h, floor_h))

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
        best_params.get(
            OPTUNA_PARAM_KEY_MIN_COVERAGE,
            float(base_requirements.config.min_coverage),
        )
    )
    coverage = min(1.0, max(OPTUNA_MIN_COVERAGE_FLOOR, coverage))
    base_hallway_count = int(getattr(base_requirements.config, "hallway_count", 1))
    hallway_count = int(best_params.get(OPTUNA_PARAM_KEY_HALLWAY_COUNT, base_hallway_count))
    hallway_count = max(OPTUNA_HALLWAY_COUNT_MIN, min(OPTUNA_HALLWAY_COUNT_MAX, hallway_count))

    tuned_config = ConfigData(
        min_coverage=coverage,
        hallway_count=hallway_count,
        max_aspect_ratio=base_requirements.config.max_aspect_ratio,
        min_aspect_ratio=base_requirements.config.min_aspect_ratio,
        floor_plan_width=floor_w,
        floor_plan_height=floor_h,
        envelope_enabled=bool(
            getattr(
                base_requirements.config,
                "envelope_enabled",
                OPTUNA_ENVELOPE_ENABLED_DEFAULT,
            )
        ),
        envelope_min_gap=int(
            getattr(
                base_requirements.config,
                "envelope_min_gap",
                OPTUNA_ENVELOPE_MIN_GAP_DEFAULT,
            )
        ),
        envelope_max_gap=int(
            getattr(
                base_requirements.config,
                "envelope_max_gap",
                OPTUNA_ENVELOPE_MAX_GAP_DEFAULT,
            )
        ),
        envelope_exclude_types=list(
            getattr(
                base_requirements.config,
                "envelope_exclude_types",
                OPTUNA_ENVELOPE_EXCLUDE_TYPES_DEFAULT,
            )
        ),
        envelope_apply_sides=list(
            getattr(
                base_requirements.config,
                "envelope_apply_sides",
                OPTUNA_ENVELOPE_APPLY_SIDES_DEFAULT,
            )
        ),
    )

    return FpgRequirements(
        rooms=tuned_rooms,
        config=tuned_config,
        relation_constraints=copy.deepcopy(base_requirements.relation_constraints),
    )


def run_optuna_optimization(
    base_requirements: FpgRequirements,
    evaluator: EVALUATION_FN,
    n_trials: int = OPTUNA_DEFAULT_TRIALS,
    study_name: str = OPTUNA_DEFAULT_STUDY_NAME,
    storage: str | None = None,
    floor_dimension_bounds: FLOOR_DIMENSION_BOUNDS | None = None,
) -> OptunaOptimizationResult:
    """Run Optuna optimization for floor-plan requirements."""

    best_run_by_trial: dict[int, FpgEvaluationResult] = {}
    controller = OptunaOptimizationController()

    optuna.logging.set_verbosity(optuna.logging.INFO)

    def objective(trial: optuna.Trial) -> float:
        # Check timeout before starting trial evaluation
        controller.check_timeout_and_raise()

        tracking_context = get_tracking_context()
        if tracking_context is not None:
            tracking_context.next_trial_id()
        try:
            trial_requirements = mutate_requirements(
                base_requirements,
                trial,
                floor_dimension_bounds=floor_dimension_bounds,
            )



            ok, reason = _precheck(trial_requirements)
            if not ok:
                
                trial.set_user_attr("status", "precheck_failed")
                trial.set_user_attr("reason", reason)
                trial.set_user_attr("valid", False)
                return 0.0
            # --- Optuna logging block end ---

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
        finally:
            if tracking_context is not None:
                tracking_context.clear_trial_id()

    def optimization_callback(study: optuna.Study, trial: optuna.Trial) -> None:
        """Callback to check early stopping and timeout conditions after each trial."""
        if trial.value is None:
            return

        score = float(trial.value)

        # Check if score threshold reached (early stop condition)
        if controller.should_stop_optimization(score):
            elapsed_time = controller.get_elapsed_time()
            message = (
                f"Early stop: score {score:.2f} >= threshold {controller.score_threshold}, "
                f"stopping trials after {elapsed_time:.2f}s"
            )
            study.stop()
            return

        # Check timeout
        try:
            controller.check_timeout_and_raise()
        except TrialTimeoutError:
            elapsed_time = controller.get_elapsed_time()
            message = f"Trial optimization timeout after {elapsed_time:.2f}s without feasible result"
            study.stop()
            raise

    sampler = optuna.samplers.TPESampler()

    study = optuna.create_study(
        direction="maximize",
        sampler=sampler,
        study_name=study_name,
        storage=storage,
        load_if_exists=True,
    )

    study.optimize(objective, n_trials=n_trials, callbacks=[optimization_callback])

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
            floor_dimension_bounds=floor_dimension_bounds,
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

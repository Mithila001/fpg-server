from __future__ import annotations

import copy
import time
from typing import Any, Callable

import optuna
from optuna.trial import FrozenTrial

from app.algorithms.fpg_optuna_score import score_optuna_layout
from app.algorithms.types import FpgRequirements
from app.algorithms.types.solvers import (
    FpgEvaluationResult,
    OptunaOptimizationResult,
)
from app.core.fpg_rooms.config_fpg import (
    MINIMUM_REQUIRED_FPG_SCORE,
    OPTUNA_NODE_PLACEMENT_PRIVATE,
    OPTUNA_NODE_PLACEMENT_PUBLIC,
    TRIAL_OPTIMIZATION_TIMEOUT_SECONDS,
)
from app.core.fpg_rooms.config_optuna import (
    OPTUNA_DEFAULT_STUDY_NAME,
    OPTUNA_DEFAULT_TRIALS,
    OPTUNA_HALLWAY_COUNT_MAX,
    OPTUNA_HALLWAY_COUNT_MIN,
    OPTUNA_PARAM_KEY_HALLWAY_COUNT,
)
from app.dev.dev_print import debug_log_data
from app.util.tracking import get_tracking_context
from .exceptions import TrialTimeoutError

EVALUATION_FN = Callable[[FpgRequirements, bool], FpgEvaluationResult]


def _opposite_side(side: str) -> str:
    return "right" if side == "left" else "left"


def _resolve_room_side_lock(
    room_type: str,
    private_side: str,
    public_side: str,
) -> str | None:
    normalized_room_type = room_type.strip()
    if normalized_room_type in OPTUNA_NODE_PLACEMENT_PRIVATE:
        return private_side
    if normalized_room_type in OPTUNA_NODE_PLACEMENT_PUBLIC:
        return public_side
    return None


def _apply_side_lock_to_x_bounds(
    min_x: float,
    max_x: float,
    side: str | None,
) -> tuple[float, float]:
    if side is None:
        return min_x, max_x

    midpoint = (float(min_x) + float(max_x)) / 2.0
    if side == "left":
        clamped_min = float(min_x)
        clamped_max = min(float(max_x), midpoint)
        if clamped_min <= clamped_max:
            return clamped_min, clamped_max
        return midpoint, midpoint

    clamped_min = max(float(min_x), midpoint)
    clamped_max = float(max_x)
    if clamped_min <= clamped_max:
        return clamped_min, clamped_max
    return midpoint, midpoint


def _normalize_score(score: float, max_score: float) -> float:
    return max(0.0, min(float(max_score), float(score)))


def _weighted_graph_score(graph_total_score: float) -> float:
    return (_normalize_score(graph_total_score, 90.0) / 90.0) * 90.0


def _weighted_solver_score(solver_total_score: float) -> float:
    return (_normalize_score(solver_total_score, 100.0) / 100.0) * 10.0


def _effective_sampling_radius(boundary_width: float, boundary_height: float) -> float:
    half_width = max(1.0, boundary_width / 2.0)
    half_height = max(1.0, boundary_height / 2.0)
    return max(
        1.0,
        min(8.0, half_width, half_height),
    )


def _sorted_rooms_for_sampling(requirements: FpgRequirements) -> list[Any]:
    priority_map = {
        "veranda": 0,
        "garage": 0,
        "livingRoom": 1,
        "diningRoom": 2,
        "kitchen": 3,
        "bathroom": 4,
    }
    return sorted(
        requirements.rooms,
        key=lambda room: (priority_map.get(getattr(room, "type", ""), 3), room.name),
    )


def _hallway_names(hallway_count: int) -> list[str]:
    return [f"hallway{index}" for index in range(1, max(0, int(hallway_count)) + 1)]


class OptunaOptimizationController:
    """Controller to manage trial optimization early stopping and timeout logic."""

    def __init__(
        self,
        timeout_seconds: float = TRIAL_OPTIMIZATION_TIMEOUT_SECONDS,
        score_threshold: float = MINIMUM_REQUIRED_FPG_SCORE,
    ):
        self.timeout_seconds = timeout_seconds
        self.score_threshold = score_threshold
        self.start_time = time.time()
        self.best_score: float | None = None

    def get_elapsed_time(self) -> float:
        return time.time() - self.start_time

    def check_timeout_and_raise(self) -> None:
        elapsed = self.get_elapsed_time()
        if elapsed > self.timeout_seconds:
            raise TrialTimeoutError(
                elapsed_time=elapsed, timeout_seconds=int(self.timeout_seconds)
            )

    def record_best_score(self, score: float) -> None:
        if self.best_score is None or score > self.best_score:
            self.best_score = score


def run_optuna_optimization(
    base_requirements: FpgRequirements,
    evaluator: EVALUATION_FN,
    n_trials: int = OPTUNA_DEFAULT_TRIALS,
    study_name: str = OPTUNA_DEFAULT_STUDY_NAME,
    storage: str | None = None,
) -> OptunaOptimizationResult:
    """Run graph-first Optuna trials and invoke solver only for high-scoring graph candidates."""
    best_run_by_trial: dict[int, FpgEvaluationResult] = {}
    controller = OptunaOptimizationController()

    optuna.logging.set_verbosity(optuna.logging.WARN)

    def objective(trial: optuna.Trial) -> float:
        controller.check_timeout_and_raise()
        tracking_context = get_tracking_context()
        if tracking_context is not None:
            tracking_context.next_trial_id()

        try:
            hallway_count = trial.suggest_int(
                OPTUNA_PARAM_KEY_HALLWAY_COUNT,
                OPTUNA_HALLWAY_COUNT_MIN,
                OPTUNA_HALLWAY_COUNT_MAX,
            )
            print(f"\nHallway Count {hallway_count}\n")
            print(
                f"Floor Plan Width and Height: W {base_requirements.config.floor_plan_width} | H {base_requirements.config.floor_plan_height}"
            )
            base_requirements.config.hallway_count = hallway_count
            sampling_radius = _effective_sampling_radius(
                boundary_width=float(base_requirements.config.floor_plan_width),
                boundary_height=float(base_requirements.config.floor_plan_height),
            )

            explicit_positions: dict[str, tuple[float, float]] = {}
            sampled_positions: dict[str, dict[str, float | str]] = {}
            for room in _sorted_rooms_for_sampling(base_requirements):
                trial.set_user_attr(
                    "fpg_current_room_context",
                    {
                        "room_id": room.name,
                        "room_name": room.name,
                        "room_type": room.type,
                        "radius": sampling_radius,
                        "floor_width": float(base_requirements.config.floor_plan_width),
                        "floor_height": float(
                            base_requirements.config.floor_plan_height
                        ),
                    },
                )

                min_x = sampling_radius
                max_x = max(
                    min_x,
                    float(base_requirements.config.floor_plan_width) - sampling_radius,
                )
                min_y = sampling_radius
                max_y = max(
                    min_y,
                    float(base_requirements.config.floor_plan_height) - sampling_radius,
                )

                sample_x = trial.suggest_float(f"{room.name}_x", min_x, max_x)
                sample_y = trial.suggest_float(f"{room.name}_y", min_y, max_y)

                explicit_positions[room.name] = (float(sample_x), float(sample_y))
                sampled_positions[room.name] = {
                    "type": room.type,
                    "x": float(sample_x),
                    "y": float(sample_y),
                    "radius": sampling_radius,
                }
                trial.set_user_attr("fpg_sampled_positions", sampled_positions)

            for hallway_name in _hallway_names(hallway_count):
                trial.set_user_attr(
                    "fpg_current_room_context",
                    {
                        "room_id": hallway_name,
                        "room_name": hallway_name,
                        "room_type": "hallway",
                        "radius": sampling_radius,
                        "floor_width": float(base_requirements.config.floor_plan_width),
                        "floor_height": float(
                            base_requirements.config.floor_plan_height
                        ),
                    },
                )

                min_x = sampling_radius
                max_x = max(
                    min_x,
                    float(base_requirements.config.floor_plan_width) - sampling_radius,
                )
                min_y = sampling_radius
                max_y = max(
                    min_y,
                    float(base_requirements.config.floor_plan_height) - sampling_radius,
                )

                sample_x = trial.suggest_float(f"{hallway_name}_x", min_x, max_x)
                sample_y = trial.suggest_float(f"{hallway_name}_y", min_y, max_y)

                explicit_positions[hallway_name] = (float(sample_x), float(sample_y))
                sampled_positions[hallway_name] = {
                    "type": "hallway",
                    "x": float(sample_x),
                    "y": float(sample_y),
                    "radius": sampling_radius,
                }
                trial.set_user_attr("fpg_sampled_positions", sampled_positions)

            score_result = score_optuna_layout(
                requirements=base_requirements,
                sampled_positions=sampled_positions,
                save_debug_plots=True,
            )
            debug_log_data({"trial_number": trial.number}, tag="[Optuna] Trial Number")
            debug_log_data(score_result, tag="[Optuna] Optuna Score Result")

            optuna_score = float(score_result.total_score)
            trial.set_user_attr("optuna_score", optuna_score)
            trial.set_user_attr("optuna_section_scores", score_result.section_scores)
            trial.set_user_attr("optuna_usable_layout", score_result.usable_layout)
            trial.set_user_attr("solver_score", 0.0)
            trial.set_user_attr("solver_weighted_score", 0.0)
            trial.set_user_attr("solver_invoked", False)
            trial.set_user_attr("solver_passed", False)

            if not score_result.usable_layout:
                trial.set_user_attr("status", "score_below_solver_gate")
                trial.set_user_attr("composite_score", optuna_score)
                print(
                    f"[Optuna] trial={trial.number} score={optuna_score:.2f} solver=SKIP reason=score_below_gate "
                    f"composite={optuna_score:.2f}"
                )
                return optuna_score

            # Stage 2: Inner Solver Evaluation (Inject Hint Logic)
            point_hints = [
                {
                    "name": room_name,
                    "type": str(position_data["type"]),
                    "x": int(round(float(position_data["x"]))),
                    "y": int(round(float(position_data["y"]))),
                }
                for room_name, position_data in sampled_positions.items()
            ]
            inner_requirements = copy.deepcopy(base_requirements)
            inner_requirements.initial_point_hints = point_hints

            inner_requirements = _update_hallway_count_for_solver(inner_requirements)

            debug_log_data(inner_requirements, tag="[Optuna] Inner Requirements")

            trial.set_user_attr("solver_invoked", True)
            run_result = evaluator(inner_requirements, False)
            trial.set_user_attr("status", run_result.status)
            trial.set_user_attr("solved", run_result.solved)

            if not run_result.solved or run_result.score_report is None:
                debug_log_data(
                    run_result.score_report, tag="[Optuna] Solver Failure Result"
                )
                trial.set_user_attr("composite_score", optuna_score)
                print(
                    f"[Optuna] trial={trial.number} score={optuna_score:.2f} solver=FAILED composite={optuna_score:.2f}"
                )
                return optuna_score

            solver_score = float(run_result.score_report.total_score)
            weighted_solver_score = _weighted_solver_score(solver_score)
            solver_passed = solver_score >= MINIMUM_REQUIRED_FPG_SCORE

            trial.set_user_attr("solver_score", solver_score)
            trial.set_user_attr("solver_weighted_score", weighted_solver_score)
            trial.set_user_attr("solver_passed", solver_passed)

            if not solver_passed:
                trial.set_user_attr("composite_score", optuna_score)
                print(
                    f"[Optuna] trial={trial.number} score={optuna_score:.2f} solver={solver_score:.2f} "
                    f"solver_w={weighted_solver_score:.2f} composite={optuna_score:.2f} solver_passed=False"
                )
                return optuna_score

            final_composite_score = optuna_score
            trial.set_user_attr("composite_score", final_composite_score)

            best_run_by_trial[trial.number] = run_result

            debug_log_data(
                run_result.score_report, tag="[Optuna] Solver Success Result"
            )
            print(
                f"[Optuna] trial={trial.number} score={optuna_score:.2f} solver={solver_score:.2f} "
                f"solver_w={weighted_solver_score:.2f} composite={final_composite_score:.2f} solver_passed={solver_passed}"
            )

            return final_composite_score

        finally:
            if tracking_context is not None:
                tracking_context.clear_trial_id()

    def optimization_callback(study: optuna.Study, trial: FrozenTrial) -> None:
        if trial.value is None:
            return
        controller.record_best_score(float(trial.value))

        if bool(trial.user_attrs.get("solver_passed", False)):
            study.stop()
            return

        if float(trial.value) >= controller.score_threshold:
            study.stop()
            return

        try:
            controller.check_timeout_and_raise()
        except TrialTimeoutError:
            study.stop()

    study = optuna.create_study(
        direction="maximize",
        study_name=study_name,
        storage=storage,
        load_if_exists=True,
    )

    try:
        study.optimize(objective, n_trials=n_trials, callbacks=[optimization_callback])
    except TrialTimeoutError:
        pass

    failed_trials = sum(1 for t in study.trials if float(t.value or 0.0) <= 0.0)

    best_trial_number = study.best_trial.number if study.best_trial else 0
    best_value = float(study.best_value) if study.best_trial else 0.0
    best_params = dict(study.best_params) if study.best_trial else {}

    best_run = best_run_by_trial.get(best_trial_number)

    return OptunaOptimizationResult(
        study.study_name,
        best_value,
        best_trial_number,
        best_params,
        len(study.trials),
        failed_trials,
        best_run,
    )


def _update_hallway_count_for_solver(requirements: FpgRequirements) -> FpgRequirements:
    """
    Synchronizes the config hallway count with the actual number of
    hallway hints generated during the graph layout stage.
    """
    if not requirements.initial_point_hints:
        requirements.config.hallway_count = 0
        return requirements

    hallway_count = sum(
        1 for hint in requirements.initial_point_hints if hint.get("type") == "hallway"
    )

    requirements.config.hallway_count = hallway_count
    return requirements

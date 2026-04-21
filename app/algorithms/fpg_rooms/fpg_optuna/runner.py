from __future__ import annotations

import copy
import time
from typing import Callable

import optuna

from app.algorithms.fpg_rooms.types.room import FpgRequirements
from app.algorithms.fpg_rooms.fpg_graph.api import run_graph_layout
from app.core.fpg_rooms.config_fpg import (
    TRIAL_EARLY_STOP_SCORE_THRESHOLD,
    TRIAL_OPTIMIZATION_TIMEOUT_SECONDS,
)
from app.core.fpg_rooms.config_optuna import (
    OPTUNA_DEFAULT_STUDY_NAME,
    OPTUNA_DEFAULT_TRIALS,
    OPTUNA_HALLWAY_COUNT_MAX,
    OPTUNA_HALLWAY_COUNT_MIN,
    OPTUNA_PARAM_KEY_HALLWAY_COUNT,
)
from app.util.tracking import get_tracking_context
from .exceptions import TrialTimeoutError
from .types import FpgEvaluationResult, OptunaOptimizationResult

EVALUATION_FN = Callable[[FpgRequirements, bool], FpgEvaluationResult]


def _normalize_score_0_100(score: float) -> float:
    return max(0.0, min(100.0, float(score)))


def _weighted_graph_score(graph_total_score: float) -> float:
    return (_normalize_score_0_100(graph_total_score) / 100.0) * 90.0


def _weighted_solver_score(solver_total_score: float) -> float:
    return (_normalize_score_0_100(solver_total_score) / 100.0) * 10.0

class OptunaOptimizationController:
    """Controller to manage trial optimization early stopping and timeout logic."""
    def __init__(
        self,
        timeout_seconds: float = TRIAL_OPTIMIZATION_TIMEOUT_SECONDS,
        score_threshold: float = TRIAL_EARLY_STOP_SCORE_THRESHOLD,
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
            raise TrialTimeoutError(elapsed_time=elapsed, timeout_seconds=self.timeout_seconds)

    def should_stop_optimization(self, score: float) -> bool:
        if self.best_score is None or score > self.best_score:
            self.best_score = score
        if score >= self.score_threshold:
            return True
        return False


def run_optuna_optimization(
    base_requirements: FpgRequirements,
    evaluator: EVALUATION_FN,
    n_trials: int = OPTUNA_DEFAULT_TRIALS,
    study_name: str = OPTUNA_DEFAULT_STUDY_NAME,
    storage: str | None = None,
) -> OptunaOptimizationResult:
    """Optuna optimization loop: build trial graphs and execute inner solver when graphs are usable."""
    best_run_by_trial: dict[int, FpgEvaluationResult] = {}
    controller = OptunaOptimizationController()

    optuna.logging.set_verbosity(optuna.logging.WARN)

    def objective(trial: optuna.Trial) -> float:
        controller.check_timeout_and_raise()
        tracking_context = get_tracking_context()
        if tracking_context is not None:
            tracking_context.next_trial_id()

        try:
            seed = trial.suggest_int("seed", 0, 9999)
            hallway_count = trial.suggest_int(
                OPTUNA_PARAM_KEY_HALLWAY_COUNT,
                OPTUNA_HALLWAY_COUNT_MIN,
                OPTUNA_HALLWAY_COUNT_MAX,
            )

            # Stage 1: Fast Graph Construction
            graph_result = run_graph_layout(
                requirements=base_requirements,
                hallway_count_override=hallway_count,
                seed=seed,
            )

            graph_score = float(graph_result.score.total_score)
            weighted_graph_score = _weighted_graph_score(graph_score)

            trial.set_user_attr("graph_score", graph_score)
            trial.set_user_attr("graph_nodes", len(graph_result.nodes))

            if not graph_result.score.usable_layout:
                trial.set_user_attr("status", "graph_unusable")
                best_run_by_trial[trial.number] = FpgEvaluationResult(
                    solved=False,
                    solution=[],
                    score_report=None,
                    status="graph_unusable",
                    message="Graph layout marked as not usable.",
                )
                return weighted_graph_score

            # Stage 2: Inner Solver Evaluation (Inject Hint Logic)
            point_hints = [
                {
                    "name": node.name,
                    "type": node.room_type,
                    "x": int(round(node.x)),
                    "y": int(round(node.y)),
                }
                for node in graph_result.nodes
            ]

            inner_requirements = copy.deepcopy(base_requirements)
            inner_requirements.initial_point_hints = point_hints

            # Execute run_solver_with_hints securely.
            run_result = evaluator(inner_requirements, False)

            best_run_by_trial[trial.number] = run_result
            trial.set_user_attr("status", run_result.status)
            trial.set_user_attr("solved", run_result.solved)

            if not run_result.solved or run_result.score_report is None:
                return weighted_graph_score

            solver_score = float(run_result.score_report.total_score)
            final_composite_score = weighted_graph_score + _weighted_solver_score(solver_score)

            return final_composite_score
            
        finally:
            if tracking_context is not None:
                tracking_context.clear_trial_id()

    def optimization_callback(study: optuna.Study, trial: optuna.Trial) -> None:
        if trial.value is None:
            return
        if controller.should_stop_optimization(float(trial.value)):
            study.stop()
        try:
            controller.check_timeout_and_raise()
        except TrialTimeoutError:
            study.stop()

    sampler = optuna.samplers.TPESampler()
    study = optuna.create_study(
        direction="maximize",
        sampler=sampler,
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
    if best_run is None:
        best_run = FpgEvaluationResult(
            solved=False,
            solution=[],
            score_report=None,
            status="missing_best_run",
            message="Optuna trial result cache empty for the best trial.",
        )

    return OptunaOptimizationResult(
        study_name=study.study_name,
        best_value=best_value,
        best_trial_number=best_trial_number,
        best_params=best_params,
        completed_trials=len(study.trials),
        failed_trials=failed_trials,
        best_run=best_run,
    )

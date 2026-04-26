from __future__ import annotations

import copy
import time
from typing import Callable

import optuna

from app.algorithms.types import FpgRequirements
from app.algorithms.fpg_rooms.fpg_graph.api import run_graph_layout
from app.algorithms.fpg_rooms.fpg_graph.adapters import build_boundary, build_nodes
from app.core.fpg_rooms.config_fpg import (
    TRIAL_EARLY_STOP_SCORE_THRESHOLD,
    TRIAL_GRAPH_SOLVER_GATE_THRESHOLD,
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
from app.algorithms.types.solvers import FpgEvaluationResult, OptunaOptimizationResult

EVALUATION_FN = Callable[[FpgRequirements, bool], FpgEvaluationResult]


def _normalize_score(score: float, max_score: float) -> float:
    return max(0.0, min(float(max_score), float(score)))


def _weighted_graph_score(graph_total_score: float) -> float:
    return (_normalize_score(graph_total_score, 90.0) / 90.0) * 90.0


def _weighted_solver_score(solver_total_score: float) -> float:
    return (_normalize_score(solver_total_score, 100.0) / 100.0) * 10.0


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
            raise TrialTimeoutError(
                elapsed_time=elapsed, timeout_seconds=self.timeout_seconds
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

            boundary = build_boundary(base_requirements)
            print(f"\nHallway Count {hallway_count}\n")
            trial_nodes = build_nodes(
                base_requirements, hallway_count_override=hallway_count
            )
            # print(f"\nBase Requirements: {base_requirements}\n")

            explicit_positions: dict[str, tuple[float, float]] = {}
            for node in trial_nodes:
                min_x = node.radius
                max_x = max(min_x, boundary.width - node.radius)
                min_y = node.radius
                max_y = max(min_y, boundary.height - node.radius)

                sample_x = trial.suggest_float(f"{node.id}_x", min_x, max_x)
                sample_y = trial.suggest_float(f"{node.id}_y", min_y, max_y)
                explicit_positions[node.id] = (sample_x, sample_y)

            # Stage 1: Fast Graph Construction
            graph_result = run_graph_layout(
                requirements=base_requirements,
                hallway_count_override=hallway_count,
                explicit_positions=explicit_positions,
            )

            graph_score = float(graph_result.score.total_score)
            weighted_graph_score = _weighted_graph_score(graph_score)

            trial.set_user_attr("graph_score", graph_score)
            trial.set_user_attr("graph_weighted_score", weighted_graph_score)
            trial.set_user_attr("graph_nodes", len(graph_result.nodes))
            trial.set_user_attr("solver_score", 0.0)
            trial.set_user_attr("solver_weighted_score", 0.0)
            trial.set_user_attr("solver_invoked", False)
            trial.set_user_attr("solver_passed", False)

            if not graph_result.score.usable_layout:
                trial.set_user_attr("status", "graph_unusable")
                best_run_by_trial[trial.number] = FpgEvaluationResult(
                    solved=False,
                    solution=[],
                    score_report=None,
                    status="graph_unusable",
                    message="Graph layout marked as not usable.",
                )
                print(
                    f"[Optuna] trial={trial.number} graph={graph_score:.2f} "
                    f"graph_w={weighted_graph_score:.2f} solver=SKIP reason=graph_unusable "
                    f"composite={weighted_graph_score:.2f}"
                )
                return weighted_graph_score

            if graph_score < TRIAL_GRAPH_SOLVER_GATE_THRESHOLD:
                trial.set_user_attr("status", "graph_below_solver_gate")
                best_run_by_trial[trial.number] = FpgEvaluationResult(
                    solved=False,
                    solution=[],
                    score_report=None,
                    status="graph_below_solver_gate",
                    message=(
                        "Graph score below solver gate threshold "
                        f"{TRIAL_GRAPH_SOLVER_GATE_THRESHOLD:.1f}."
                    ),
                )
                print(
                    f"[Optuna] trial={trial.number} graph={graph_score:.2f} "
                    f"graph_w={weighted_graph_score:.2f} solver=SKIP reason=graph_below_gate "
                    f"gate={TRIAL_GRAPH_SOLVER_GATE_THRESHOLD:.2f} composite={weighted_graph_score:.2f}"
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

            # print(f"Inner Requirements: {inner_requirements}\n")

            inner_requirements = _update_hallway_count_for_solver(inner_requirements)

            # Execute run_solver_with_hints securely.
            trial.set_user_attr("solver_invoked", True)
            run_result = evaluator(inner_requirements, False)

            best_run_by_trial[trial.number] = run_result
            trial.set_user_attr("status", run_result.status)
            trial.set_user_attr("solved", run_result.solved)

            if not run_result.solved or run_result.score_report is None:
                print(
                    f"[Optuna] trial={trial.number} graph={graph_score:.2f} "
                    f"graph_w={weighted_graph_score:.2f} solver=FAILED composite={weighted_graph_score:.2f}"
                )
                return weighted_graph_score

            solver_score = float(run_result.score_report.total_score)
            weighted_solver_score = _weighted_solver_score(solver_score)
            final_composite_score = weighted_graph_score + weighted_solver_score
            solver_passed = solver_score >= TRIAL_EARLY_STOP_SCORE_THRESHOLD

            trial.set_user_attr("solver_score", solver_score)
            trial.set_user_attr("solver_weighted_score", weighted_solver_score)
            trial.set_user_attr("solver_passed", solver_passed)
            trial.set_user_attr("composite_score", final_composite_score)

            print(
                f"[Optuna] trial={trial.number} graph={graph_score:.2f} graph_w={weighted_graph_score:.2f} "
                f"solver={solver_score:.2f} solver_w={weighted_solver_score:.2f} "
                f"composite={final_composite_score:.2f} solver_passed={solver_passed}"
            )

            return final_composite_score

        finally:
            if tracking_context is not None:
                tracking_context.clear_trial_id()

    def optimization_callback(study: optuna.Study, trial: optuna.Trial) -> None:
        if trial.value is None:
            return
        controller.record_best_score(float(trial.value))

        if bool(trial.user_attrs.get("solver_passed", False)):
            study.stop()
            return

        try:
            solver_score = float(trial.user_attrs.get("solver_score", 0.0))
        except (TypeError, ValueError):
            solver_score = 0.0

        if solver_score >= controller.score_threshold:
            study.stop()
            return

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

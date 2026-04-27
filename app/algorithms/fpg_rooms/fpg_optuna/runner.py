from __future__ import annotations

import copy
import math
import time
from typing import Callable

import optuna
from optuna.trial import FrozenTrial

from app.algorithms.types import FpgRequirements
from app.algorithms.fpg_rooms.fpg_graph.api import run_graph_layout
from app.algorithms.fpg_rooms.fpg_graph.adapters import build_boundary, build_nodes
from app.algorithms.types.solvers import (
    FpgEvaluationResult,
    GraphPhysicsConfig,
    OptunaOptimizationResult,
)
from app.core.fpg_rooms.config_fpg import (
    MINIMUM_REQUIRED_FPG_SCORE,
    OPTUNA_NODE_PLACEMENT_PRIVATE,
    OPTUNA_NODE_PLACEMENT_PUBLIC,
    TRIAL_GRAPH_SOLVER_GATE_THRESHOLD,
    TRIAL_OPTIMIZATION_TIMEOUT_SECONDS,
)
from app.core.fpg_rooms.config_optuna import (
    OPTUNA_DEFAULT_STUDY_NAME,
    OPTUNA_DEFAULT_TRIALS,
    OPTUNA_GRAPH_PHASE1_ITERATIONS,
    OPTUNA_GRAPH_PHASE1_UNIFORM_RADIUS,
    OPTUNA_GRAPH_PHASE2_ITERATIONS,
    OPTUNA_HALLWAY_COUNT_MAX,
    OPTUNA_HALLWAY_COUNT_MIN,
    OPTUNA_NODE_PLACEMENT_SAMPLING_RADIUS,
    OPTUNA_PARAM_KEY_HALLWAY_COUNT,
)
from app.dev.dev_print import debug_log_data
from app.util.tracking import get_tracking_context
from .exceptions import TrialTimeoutError
from .sampling_logic import RoomAwareTPESampler, RoomSamplingPolicy

EVALUATION_FN = Callable[[FpgRequirements, bool], FpgEvaluationResult]
OPTUNA_SEARCH_SPACE_GRID_SCALE = 10
OPTUNA_PARAM_KEY_PRIVATE_SIDE = "private_side"


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
        min(float(OPTUNA_NODE_PLACEMENT_SAMPLING_RADIUS), half_width, half_height),
    )


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
    sampling_policy = RoomSamplingPolicy()

    optuna.logging.set_verbosity(optuna.logging.WARN)

    def objective(trial: optuna.Trial) -> float:
        controller.check_timeout_and_raise()
        tracking_context = get_tracking_context()
        if tracking_context is not None:
            tracking_context.next_trial_id()

        try:
            private_side = trial.suggest_categorical(
                OPTUNA_PARAM_KEY_PRIVATE_SIDE, ["left", "right"]
            )
            public_side = _opposite_side(str(private_side))
            trial.set_user_attr("fpg_private_side", private_side)
            trial.set_user_attr("fpg_public_side", public_side)

            hallway_count = trial.suggest_int(
                OPTUNA_PARAM_KEY_HALLWAY_COUNT,
                OPTUNA_HALLWAY_COUNT_MIN,
                OPTUNA_HALLWAY_COUNT_MAX,
            )

            boundary = build_boundary(base_requirements)
            print(f"\nHallway Count {hallway_count}\n")
            base_requirements.config.hallway_count = hallway_count
            trial_nodes = sampling_policy.sort_nodes_for_sampling(
                build_nodes(base_requirements)
            )
            # print(f"\nBase Requirements: {base_requirements}\n")

            sampling_radius = _effective_sampling_radius(
                boundary_width=boundary.width,
                boundary_height=boundary.height,
            )

            explicit_positions: dict[str, tuple[float, float]] = {}
            sampled_positions: dict[str, dict[str, float | str]] = {}
            used_positions: set[tuple[float, float]] = set()
            for node in trial_nodes:
                trial.set_user_attr(
                    "fpg_current_room_context",
                    {
                        "room_id": node.id,
                        "room_name": node.name,
                        "room_type": node.room_type,
                        "radius": sampling_radius,
                        "floor_width": boundary.width,
                        "floor_height": boundary.height,
                    },
                )

                min_x = sampling_radius
                max_x = max(min_x, boundary.width - sampling_radius)
                min_y = sampling_radius
                max_y = max(min_y, boundary.height - sampling_radius)

                room_side_lock = _resolve_room_side_lock(
                    room_type=node.room_type,
                    private_side=str(private_side),
                    public_side=public_side,
                )
                min_x, max_x = _apply_side_lock_to_x_bounds(
                    min_x=min_x,
                    max_x=max_x,
                    side=room_side_lock,
                )

                min_x_idx = int(math.ceil(min_x / OPTUNA_SEARCH_SPACE_GRID_SCALE))
                max_x_idx = int(math.floor(max_x / OPTUNA_SEARCH_SPACE_GRID_SCALE))
                if min_x_idx > max_x_idx:
                    x_idx = min_x_idx
                else:
                    x_idx = trial.suggest_int(f"{node.id}_x_idx", min_x_idx, max_x_idx)

                if min_y > max_y:
                    sample_y = float(min_y)
                else:
                    sample_y = trial.suggest_float(f"{node.id}_y", min_y, max_y)

                sample_x = float(x_idx * OPTUNA_SEARCH_SPACE_GRID_SCALE)
                sampled_position = (sample_x, sample_y)

                if sampled_position in used_positions:
                    trial.set_user_attr("status", "duplicate_grid_position")
                    trial.set_user_attr("composite_score", 0.0)
                    print(
                        f"[Optuna] trial={trial.number} solver=SKIP reason=duplicate_grid_position "
                        f"node={node.id} position={sampled_position}"
                    )
                    return 0.0

                used_positions.add(sampled_position)
                explicit_positions[node.id] = (sample_x, sample_y)
                sampled_positions[node.id] = {
                    "type": node.room_type,
                    "x": sample_x,
                    "y": sample_y,
                    "radius": sampling_radius,
                }
                trial.set_user_attr("fpg_sampled_positions", sampled_positions)

            # Stage 1: Fast Graph Construction
            graph_result = run_graph_layout(
                requirements=base_requirements,
                explicit_positions=explicit_positions,
                plot_base_name=f"trial_{trial.number}_phase_layout",
                physics_config=GraphPhysicsConfig(
                    use_staged_node_sizing=True,
                    staged_uniform_radius=OPTUNA_GRAPH_PHASE1_UNIFORM_RADIUS,
                    staged_phase1_iterations=OPTUNA_GRAPH_PHASE1_ITERATIONS,
                    staged_phase2_iterations=OPTUNA_GRAPH_PHASE2_ITERATIONS,
                ),
            )
            debug_log_data({"trial_number": trial.number}, tag="[Optuna] Trial Number")
            debug_log_data(graph_result, tag="[Optuna] Graph Result")

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
                trial.set_user_attr("composite_score", 0.0)
                print(
                    f"[Optuna] trial={trial.number} graph={graph_score:.2f} "
                    f"graph_w={weighted_graph_score:.2f} solver=SKIP reason=graph_unusable "
                    f"composite=0.00"
                )
                return 0.0

            if graph_score <= TRIAL_GRAPH_SOLVER_GATE_THRESHOLD:
                trial.set_user_attr("status", "graph_below_solver_gate")
                trial.set_user_attr("composite_score", 0.0)
                print(
                    f"[Optuna] trial={trial.number} graph={graph_score:.2f} "
                    f"graph_w={weighted_graph_score:.2f} solver=SKIP reason=graph_below_gate "
                    f"gate={TRIAL_GRAPH_SOLVER_GATE_THRESHOLD:.2f} composite=0.00"
                )
                return 0.0

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
            debug_log_data(base_requirements, tag="[Optuna] Base Requirements")
            inner_requirements = copy.deepcopy(base_requirements)
            inner_requirements.initial_point_hints = point_hints

            # print(f"Inner Requirements: {inner_requirements}\n")

            inner_requirements = _update_hallway_count_for_solver(inner_requirements)

            debug_log_data(inner_requirements, tag="[Optuna] Inner Requirements")

            # Execute run_solver_with_hints securely.
            trial.set_user_attr("solver_invoked", True)
            run_result = evaluator(inner_requirements, False)
            trial.set_user_attr("status", run_result.status)
            trial.set_user_attr("solved", run_result.solved)

            if not run_result.solved or run_result.score_report is None:
                debug_log_data(
                    run_result.score_report, tag="[Optuna] Solver Failure Result"
                )
                trial.set_user_attr("composite_score", 0.0)
                print(
                    f"[Optuna] trial={trial.number} graph={graph_score:.2f} "
                    f"graph_w={weighted_graph_score:.2f} solver=FAILED composite=0.00"
                )
                return 0.0

            solver_score = float(run_result.score_report.total_score)
            weighted_solver_score = _weighted_solver_score(solver_score)
            solver_passed = solver_score >= MINIMUM_REQUIRED_FPG_SCORE

            trial.set_user_attr("solver_score", solver_score)
            trial.set_user_attr("solver_weighted_score", weighted_solver_score)
            trial.set_user_attr("solver_passed", solver_passed)

            if not solver_passed:
                trial.set_user_attr("composite_score", 0.0)
                print(
                    f"[Optuna] trial={trial.number} graph={graph_score:.2f} graph_w={weighted_graph_score:.2f} "
                    f"solver={solver_score:.2f} solver_w={weighted_solver_score:.2f} "
                    f"composite=0.00 solver_passed=False"
                )
                return 0.0

            final_composite_score = weighted_graph_score + weighted_solver_score
            trial.set_user_attr("composite_score", final_composite_score)

            best_run_by_trial[trial.number] = run_result

            debug_log_data(
                run_result.score_report, tag="[Optuna] Solver Success Result"
            )
            print(
                f"[Optuna] trial={trial.number} graph={graph_score:.2f} graph_w={weighted_graph_score:.2f} "
                f"solver={solver_score:.2f} solver_w={weighted_solver_score:.2f} "
                f"composite={final_composite_score:.2f} solver_passed={solver_passed}"
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

    sampler = RoomAwareTPESampler(policy=sampling_policy)
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

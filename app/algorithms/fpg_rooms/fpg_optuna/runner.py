from __future__ import annotations

import copy
import time
from typing import Any, Callable, Mapping, Sequence

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
    OPTUNA_SEARCH_SPACE_GRID_SCALE,
    TRIAL_OPTIMIZATION_TIMEOUT_SECONDS,
)
from app.core.fpg_rooms.config_optuna import (
    OPTUNA_DEFAULT_STUDY_NAME,
    OPTUNA_DEFAULT_TRIALS,
    OPTUNA_HALLWAY_COUNT,
)
from app.dev.dev_print import debug_log_data
from app.util.tracking import get_tracking_context
from .exceptions import TrialTimeoutError
from .sampling_logic import RoomAwareTPESampler

EVALUATION_FN = Callable[[FpgRequirements, bool], FpgEvaluationResult]
CONSTRAINTS_FN = Callable[[FrozenTrial], Sequence[float]]
PROGRESS_EMITTER = Callable[[str, str, dict[str, Any] | None], None]


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


def _snap_search_bounds_to_grid(
    min_value: float,
    max_value: float,
    grid_scale: float,
) -> tuple[float, float]:
    step = max(1.0, float(grid_scale))
    snapped_min = ((float(min_value) + step - 1e-9) // step) * step
    snapped_max = (float(max_value) // step) * step

    if snapped_min > snapped_max:
        return float(min_value), float(max_value)

    return float(snapped_min), float(snapped_max)


def _normalized_coordinate_key(
    position_data: dict[str, float | str],
) -> tuple[int, int] | None:
    try:
        return (
            int(round(float(position_data["x"]))),
            int(round(float(position_data["y"]))),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _duplicate_coordinate_count(
    sampled_positions: dict[str, dict[str, float | str]],
) -> float:
    seen_coordinates: set[tuple[int, int]] = set()
    duplicate_count = 0

    for position_data in sampled_positions.values():
        coordinate_key = _normalized_coordinate_key(position_data)
        if coordinate_key is None:
            continue
        if coordinate_key in seen_coordinates:
            duplicate_count += 1
            continue
        seen_coordinates.add(coordinate_key)

    return float(duplicate_count)


def _trial_coordinate_constraints(trial: FrozenTrial) -> Sequence[float]:
    sampled_positions = trial.user_attrs.get("fpg_sampled_positions")
    if not isinstance(sampled_positions, dict):
        return (0.0,)

    return (_duplicate_coordinate_count(sampled_positions),)


def _uncrossed_hallway_names_from_diagnostics(
    diagnostics: Mapping[str, Any] | None,
) -> set[str]:
    if not isinstance(diagnostics, Mapping):
        return set()

    room_relations = diagnostics.get("room_relations")
    if not isinstance(room_relations, Mapping):
        return set()

    uncrossed_hallways = room_relations.get("uncrossed_hallways", [])
    hallway_names: set[str] = set()

    if not isinstance(uncrossed_hallways, Sequence) or isinstance(
        uncrossed_hallways, (str, bytes)
    ):
        return hallway_names

    for hallway in uncrossed_hallways:
        hallway_name: str | None = None
        if isinstance(hallway, Mapping):
            name_value = hallway.get("name")
            if name_value is not None:
                hallway_name = str(name_value)
        else:
            name_value = getattr(hallway, "name", None)
            if name_value is not None:
                hallway_name = str(name_value)

        if hallway_name:
            hallway_names.add(hallway_name)

    return hallway_names


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
    progress_emitter: PROGRESS_EMITTER | None = None,
) -> OptunaOptimizationResult:
    """Run graph-first Optuna trials and invoke solver only for high-scoring graph candidates."""
    best_run_by_trial: dict[int, FpgEvaluationResult] = {}
    controller = OptunaOptimizationController()
    termination_reason = "trial_count_exceeded"

    def emit_progress(
        event: str, message: str, data: dict[str, Any] | None = None
    ) -> None:
        if progress_emitter is None:
            return
        try:
            progress_emitter(event, message, data)
        except Exception:
            return

    optuna.logging.set_verbosity(optuna.logging.WARN)

    def objective(trial: optuna.Trial) -> float:
        controller.check_timeout_and_raise()
        tracking_context = get_tracking_context()
        if tracking_context is not None:
            tracking_context.next_trial_id()

        emit_progress(
            "trial_started",
            f"Starting trial {trial.number + 1}.",
            {"trial_number": trial.number + 1},
        )

        try:
            hallway_count = int(OPTUNA_HALLWAY_COUNT)
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

                min_x, max_x = _snap_search_bounds_to_grid(
                    min_x, max_x, OPTUNA_SEARCH_SPACE_GRID_SCALE
                )
                min_y, max_y = _snap_search_bounds_to_grid(
                    min_y, max_y, OPTUNA_SEARCH_SPACE_GRID_SCALE
                )

                sample_x = trial.suggest_float(
                    f"{room.name}_x", min_x, max_x, step=OPTUNA_SEARCH_SPACE_GRID_SCALE
                )
                sample_y = trial.suggest_float(
                    f"{room.name}_y", min_y, max_y, step=OPTUNA_SEARCH_SPACE_GRID_SCALE
                )

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

                min_x, max_x = _snap_search_bounds_to_grid(
                    min_x, max_x, OPTUNA_SEARCH_SPACE_GRID_SCALE
                )
                min_y, max_y = _snap_search_bounds_to_grid(
                    min_y, max_y, OPTUNA_SEARCH_SPACE_GRID_SCALE
                )

                sample_x = trial.suggest_float(
                    f"{hallway_name}_x",
                    min_x,
                    max_x,
                    step=OPTUNA_SEARCH_SPACE_GRID_SCALE,
                )
                sample_y = trial.suggest_float(
                    f"{hallway_name}_y",
                    min_y,
                    max_y,
                    step=OPTUNA_SEARCH_SPACE_GRID_SCALE,
                )

                explicit_positions[hallway_name] = (float(sample_x), float(sample_y))
                sampled_positions[hallway_name] = {
                    "type": "hallway",
                    "x": float(sample_x),
                    "y": float(sample_y),
                    "radius": sampling_radius,
                }
                trial.set_user_attr("fpg_sampled_positions", sampled_positions)

            duplicate_coordinate_count = _duplicate_coordinate_count(sampled_positions)
            if duplicate_coordinate_count > 0:
                emit_progress(
                    "trial_completed",
                    "Trial rejected because of duplicate coordinates.",
                    {
                        "trial_number": trial.number + 1,
                        "status": "duplicate_coordinate_rejected",
                        "optuna_score": 0.0,
                        "solver_invoked": False,
                        "solver_passed": False,
                    },
                )
                trial.set_user_attr("optuna_score", 0.0)
                trial.set_user_attr("optuna_section_scores", {})
                trial.set_user_attr("optuna_usable_layout", False)
                trial.set_user_attr("solver_score", 0.0)
                trial.set_user_attr("solver_weighted_score", 0.0)
                trial.set_user_attr("solver_invoked", False)
                trial.set_user_attr("solver_passed", False)
                trial.set_user_attr(
                    "duplicate_coordinate_count", duplicate_coordinate_count
                )
                trial.set_user_attr("status", "duplicate_coordinate_rejected")
                trial.set_user_attr("composite_score", 0.0)
                print(
                    f"[Optuna] trial={trial.number} score=0.00 solver=SKIP reason=duplicate_coordinate_rejected "
                    f"duplicates={duplicate_coordinate_count:.0f} composite=0.00"
                )
                return 0.0

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
                emit_progress(
                    "trial_completed",
                    "Trial completed below solver gate.",
                    {
                        "trial_number": trial.number + 1,
                        "status": "score_below_solver_gate",
                        "optuna_score": optuna_score,
                        "solver_invoked": False,
                        "solver_passed": False,
                    },
                )
                trial.set_user_attr("status", "score_below_solver_gate")
                trial.set_user_attr("composite_score", optuna_score)
                print(
                    f"[Optuna] trial={trial.number} score={optuna_score:.2f} solver=SKIP reason=score_below_gate "
                    f"composite={optuna_score:.2f}"
                )
                return optuna_score

            # Stage 2: Inner Solver Evaluation (Inject Hint Logic)
            uncrossed_hallway_names = _uncrossed_hallway_names_from_diagnostics(
                score_result.diagnostics
            )

            hallway_hint_names = [
                room_name
                for room_name, position_data in sampled_positions.items()
                if str(position_data.get("type", "")) == "hallway"
            ]
            print(
                f"[Optuna] trial={trial.number} hallway_hints_before_filter="
                f"{hallway_hint_names}"
            )

            point_hints = [
                {
                    "name": room_name,
                    "type": str(position_data["type"]),
                    "x": int(round(float(position_data["x"]))),
                    "y": int(round(float(position_data["y"]))),
                }
                for room_name, position_data in sampled_positions.items()
                if not (
                    str(position_data.get("type", "")) == "hallway"
                    and room_name in uncrossed_hallway_names
                )
            ]

            filtered_hallway_names = [
                hint["name"]
                for hint in point_hints
                if str(hint.get("type", "")) == "hallway"
            ]
            print(
                f"[Optuna] trial={trial.number} hallway_hints_after_filter="
                f"{filtered_hallway_names} "
                f"filtered_out={len(hallway_hint_names) - len(filtered_hallway_names)}"
            )

            inner_requirements = copy.deepcopy(base_requirements)
            inner_requirements.initial_point_hints = point_hints

            inner_requirements = _update_hallway_count_for_solver(inner_requirements)

            debug_log_data(inner_requirements, tag="[Optuna] Inner Requirements")

            trial.set_user_attr("solver_invoked", True)
            run_result = evaluator(inner_requirements, False)
            trial.set_user_attr("status", run_result.status)
            trial.set_user_attr("solved", run_result.solved)

            if not run_result.solved or run_result.fpg_score_results is None:
                debug_log_data(
                    run_result.fpg_score_results, tag="[Optuna] Solver Failure Result"
                )
                emit_progress(
                    "trial_completed",
                    "Trial completed without a solved layout.",
                    {
                        "trial_number": trial.number + 1,
                        "status": run_result.status,
                        "optuna_score": optuna_score,
                        "solver_invoked": True,
                        "solver_passed": False,
                    },
                )
                trial.set_user_attr("composite_score", optuna_score)
                print(
                    f"[Optuna] trial={trial.number} score={optuna_score:.2f} solver=FAILED composite={optuna_score:.2f}"
                )
                return optuna_score

            fpg_score = run_result.fpg_score_results
            try:
                solver_score_value: Any = getattr(fpg_score, "critical_score", None)
                solver_score = (
                    float(solver_score_value) if solver_score_value is not None else 0.0
                )
            except Exception:
                solver_score = 0.0

            weighted_solver_score = _weighted_solver_score(solver_score)
            solver_passed = solver_score >= MINIMUM_REQUIRED_FPG_SCORE

            trial.set_user_attr("solver_score", solver_score)
            trial.set_user_attr("solver_weighted_score", weighted_solver_score)
            trial.set_user_attr("solver_passed", solver_passed)

            if not solver_passed:
                emit_progress(
                    "trial_completed",
                    "Trial completed but solver score did not pass the threshold.",
                    {
                        "trial_number": trial.number + 1,
                        "status": run_result.status,
                        "optuna_score": optuna_score,
                        "solver_score": solver_score,
                        "solver_invoked": True,
                        "solver_passed": False,
                    },
                )
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
                run_result.fpg_score_results, tag="[Optuna] Solver Success Result"
            )
            emit_progress(
                "trial_completed",
                "Trial produced a solver-passed layout.",
                {
                    "trial_number": trial.number + 1,
                    "status": run_result.status,
                    "optuna_score": optuna_score,
                    "solver_score": solver_score,
                    "solver_invoked": True,
                    "solver_passed": True,
                },
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
        sampler=RoomAwareTPESampler(constraints_func=_trial_coordinate_constraints),
        storage=storage,
        load_if_exists=True,
    )

    try:
        study.optimize(objective, n_trials=n_trials, callbacks=[optimization_callback])
    except TrialTimeoutError:
        termination_reason = "generation_time_out"
        pass
    else:
        if any(bool(t.user_attrs.get("solver_passed", False)) for t in study.trials):
            termination_reason = "success"
        else:
            termination_reason = "trial_count_exceeded"

    failed_trials = sum(1 for t in study.trials if float(t.value or 0.0) <= 0.0)

    best_trial_number = study.best_trial.number if study.best_trial else 0
    best_value = float(study.best_value) if study.best_trial else 0.0
    best_params = dict(study.best_params) if study.best_trial else {}

    best_run = best_run_by_trial.get(best_trial_number)

    # Fallback: if Optuna's best_trial doesn't have an associated solver run
    # but we have at least one solved run recorded, pick the best solved run
    # by the solver `critical_score` to avoid returning None to callers.
    if best_run is None and best_run_by_trial:

        def _score_key(r: FpgEvaluationResult) -> float:
            try:
                return float(
                    getattr(r.fpg_score_results, "critical_score", float("-inf"))
                )
            except Exception:
                return float("-inf")

        best_run = max(best_run_by_trial.values(), key=_score_key)
        try:
            print(
                f"[Optuna] best_run missing for best_trial={best_trial_number}; "
                f"falling back to best solved trial (critical_score={_score_key(best_run):.2f})"
            )
        except Exception:
            print(
                f"[Optuna] best_run missing for best_trial={best_trial_number}; falling back to best solved trial"
            )

    emit_progress(
        "optimization_completed",
        "Optuna optimization finished.",
        {
            "termination_reason": termination_reason,
            "best_trial_number": best_trial_number,
            "best_value": best_value,
            "completed_trials": len(study.trials),
            "failed_trials": failed_trials,
            "has_best_run": best_run is not None,
        },
    )

    return OptunaOptimizationResult(
        study.study_name,
        best_value,
        best_trial_number,
        best_params,
        len(study.trials),
        failed_trials,
        best_run,
        termination_reason,
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

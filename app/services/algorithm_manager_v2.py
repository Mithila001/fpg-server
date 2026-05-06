import contextlib
import io
import time
from dataclasses import asdict, is_dataclass
from typing import Any, Callable

from app.algorithms.fpg_opening_v2.fpg_opening_generator import generate_fpg_openings
from app.algorithms.fpg_post_processor.extend_walls import extend_floor_plan_walls
from app.algorithms.fpg_post_processor.simplify_rectilinear_vertices import (
    clean_floorplan_rectilinearity,
)
from app.algorithms.fpg_post_processor.snap_floor_plan_to_grid import (
    snap_floor_plan_to_grid,
)
from app.algorithms.fpg_post_processor.veranda_post_process import modify_veranda_layout
from app.algorithms.fpg_rooms import FloorPlanGenerator
from app.algorithms.fpg_rooms.fpg_optuna import (
    run_optuna_optimization,
)
from app.algorithms.types import FpgRequirements
from app.algorithms.fpg_rooms.fpg_post_process import (
    run_quick_post_process,
)
from app.algorithms.types.openings import FloorPlanWithOpenings
from app.algorithms.types.solvers.optimization import FpgEvaluationResult
from app.dev.dev_print import debug_log_data
from app.util.algorithm_manager.fpg_procesors.union_floor_plan import (
    UnionFloorPlanResult,
    union_floor_plan,
)
from app.util.logger.system_logger import SystemLogger

from app.algorithms.fgp_score.score_manager import score_manager
from app.algorithms.types.fpg_score import ScoreManagerResult
from app.algorithms.fpg_rooms.fpgr_p_refine_1 import run_refine_profile_1
from app.core.fpg_rooms.config_fpg import (
    DEFAULT_OPTUNA_STUDY_NAME,
    DEFAULT_OPTUNA_TRIALS,
    MINIMUM_REQUIRED_FPG_SCORE,
    BEST_FLOOR_PLAN_SCORE,
    DEFAULT_OPTUNA_STORAGE_ENABLED,
    DEFAULT_OPTUNA_STORAGE_URL,
    WIGGLE_ROOM,
)
from app.algorithms.types.domain import ProcessedRoomData
from app.schemas.db.room_setup_template import RoomSetupTemplateBase
from app.util.algorithm_manager import (
    build_requirements,
    validate_and_compute_floor_bounds,
)
from test.dev.final_result_plotter import plot_final_solver_result
from test.dev.plot_refiner import plot_refine_floor_plan

FPG_SOLVER_RUN_COUNT = 2


def _extract_score(run_result: FpgEvaluationResult) -> float | None:
    fpg_score = run_result.fpg_score_results
    if fpg_score is None:
        return None
    try:
        score_value: Any = getattr(fpg_score, "critical_score", None)
        return float(score_value) if score_value is not None else None
    except Exception:
        return None


def _build_result_payload(
    run_result: FpgEvaluationResult,
    score: float | None = None,
) -> dict[str, Any]:
    union_results_dict = None
    if run_result.union_results is not None:
        try:
            if is_dataclass(run_result.union_results):
                union_results_dict = asdict(run_result.union_results)
            else:
                union_results_dict = dict(run_result.union_results)

            if "floor_plan_with_openings" in union_results_dict:
                fpo = union_results_dict["floor_plan_with_openings"]
                if is_dataclass(fpo) and not isinstance(fpo, type):
                    union_results_dict["floor_plan_with_openings"] = asdict(fpo)
                elif hasattr(fpo, "__dict__"):
                    union_results_dict["floor_plan_with_openings"] = dict(fpo.__dict__)
        except Exception as exc:
            print(f"Error serializing union_results: {exc}")
            union_results_dict = None

    payload: dict[str, Any] = {
        "status": run_result.status,
        "message": run_result.message,
        "union_results": union_results_dict,
    }
    if score is not None:
        payload["score"] = round(float(score), 2)
    return payload


def _build_failure_payload(
    reason: str,
    message: str | None = None,
    details: str | None = None,
) -> dict[str, Any]:
    payload = {
        "status": "NO_FLOOR_PLAN",
        "message": message or "No floor plan found.",
        "union_results": None,
        "did_not_found_floor_plan": reason,
        "reason": reason,
    }
    if details:
        payload["details"] = details
    return payload


def _maybe_emit_best_candidate(
    run_result: FpgEvaluationResult,
    emit_progress: Callable[[str, str, dict[str, Any] | None], None],
    best_score: float | None,
) -> float | None:
    score = _extract_score(run_result)
    if score is None or score < MINIMUM_REQUIRED_FPG_SCORE:
        return best_score
    if best_score is not None and score <= best_score:
        return best_score
    payload = _build_result_payload(run_result, score)
    emit_progress(
        "current_best_updated",
        "Current best floor plan updated.",
        {"score": score, "result": payload},
    )
    return score


def _run_single_fpg_solve(
    requirements: FpgRequirements,
    verbose: bool = True,
) -> FpgEvaluationResult:
    generator = FloorPlanGenerator(requirements)
    print("\n _run_single_fpg_solve")

    verbose = False  # TODO DEBUG FLAG Remove this
    if verbose:
        solved = generator.generate()
    else:
        with contextlib.redirect_stdout(io.StringIO()):
            solved = generator.generate()

    status = generator.last_status_name
    print(f"Status:{status}")

    if not solved:
        print("\nNOT solved")
        return FpgEvaluationResult(
            solved=False,
            status=status,
            message="Solver did not return FEASIBLE/OPTIMAL",
        )

    solution = generator.get_solution()
    print("\n get solution ")
    quick_post_process_result = run_quick_post_process(
        {"rooms": solution, "openings": []}
    )
    print("\n run quick post process")

    # Normalize room dicts
    stage1_rooms = [dict(room) for room in quick_post_process_result["rooms"]]

    # --- PASS 1: Standard Refine ---
    refine_result1 = run_refine_profile_1(
        requirements=requirements,
        initial_rooms=stage1_rooms,
        wiggle_room=WIGGLE_ROOM,
        verbose=False,
    )
    print("\n run_refine_profile_1 (Pass 1)")
    stage2_rooms = refine_result1.rooms if refine_result1.rooms else stage1_rooms

    # --- PASS 2: Standard Refine ---
    refine_result2 = run_refine_profile_1(
        requirements=requirements,
        initial_rooms=stage2_rooms,
        wiggle_room=WIGGLE_ROOM,
        verbose=False,
    )
    print("\n run_refine_profile_2 (Pass 2)")
    stage3_rooms = refine_result2.rooms if refine_result2.rooms else stage2_rooms

    # --- PASS 3: Standard Refine ---
    refine_result3 = run_refine_profile_1(
        requirements=requirements,
        initial_rooms=stage3_rooms,
        wiggle_room=WIGGLE_ROOM,
        verbose=False,
    )
    print("\n run_refine_profile_3 (Pass 3)")
    final_rooms = refine_result3.rooms if refine_result3.rooms else stage3_rooms

    try:
        plot_refine_floor_plan(
            stage1_rooms=stage1_rooms,
            stage2_rooms=stage2_rooms,
            stage4_rooms=final_rooms,
        )
    except Exception as e:
        print(f"Failed to plot refine floor plan: {e}")

    # Provide a timestamped filename so the post-processor saves a plot for inspection
    timestamp = int(time.time())
    verandaUpdatedPlan = modify_veranda_layout(final_rooms)
    processed_floor_plan: list[ProcessedRoomData] = extend_floor_plan_walls(
        verandaUpdatedPlan, filename=f"refine_{timestamp}.png"
    )
    grid_snapped_floor_plan: list[ProcessedRoomData] = snap_floor_plan_to_grid(
        processed_floor_plan
    )
    cleaned_floor_plan: list[ProcessedRoomData] = clean_floorplan_rectilinearity(
        grid_snapped_floor_plan
    )
    floor_plan_with_openings: FloorPlanWithOpenings = generate_fpg_openings(
        requirements, cleaned_floor_plan
    )

    fpg_score_results: ScoreManagerResult = score_manager(
        floor_plan_with_openings, requirements
    )
    union_results: UnionFloorPlanResult = union_floor_plan(floor_plan_with_openings)

    return FpgEvaluationResult(
        solved=True,
        status=status,
        message="Solver found a layout",
        fpg_score_results=fpg_score_results,
        union_results=union_results,
    )


def run_solver_with_hints(
    requirements: FpgRequirements,
    verbose: bool = True,
    run_count: int = FPG_SOLVER_RUN_COUNT,
    progress_emitter: Callable[[str, str, dict[str, Any] | None], None] | None = None,
) -> FpgEvaluationResult:
    """Inner loop for Phase 3: repeatedly run solver with point hints and keep best solved layout."""
    safe_run_count = max(1, int(run_count))

    best_result: FpgEvaluationResult | None = None
    best_score = float("-inf")
    best_event_score: float | None = None
    last_result: FpgEvaluationResult | None = None

    def emit_progress(
        event: str, message: str, data: dict[str, Any] | None = None
    ) -> None:
        if progress_emitter is None:
            return
        try:
            progress_emitter(event, message, data)
        except Exception:
            return

    for attempt_index in range(safe_run_count):
        current_result: FpgEvaluationResult = _run_single_fpg_solve(
            requirements=requirements, verbose=verbose
        )
        print(
            f"\n[SolverLoop] Current Result Attempt {attempt_index + 1}: status={current_result.status} solved={current_result.solved}\n"
        )
        last_result = current_result

        fpg_score = current_result.fpg_score_results
        print(f"[SolverLoop] FPG Score Result: {fpg_score}\n")
        if fpg_score is None:
            current_score = None
        else:
            current_score = fpg_score.critical_score

        if current_score is None:
            print(
                f"[SolverLoop] attempt={attempt_index + 1}/{safe_run_count} missing score, skipping"
            )
            SystemLogger.log_event(
                tag="SOLVER",
                event="solver_missing_score",
                level="INFO",
                data={"attempt": attempt_index + 1, "status": current_result.status},
            )
            continue

        print(
            f"[SolverLoop] attempt={attempt_index + 1}/{safe_run_count} "
            f"status={current_result.status} score={current_score:.2f}"
        )

        best_event_score = _maybe_emit_best_candidate(
            current_result, emit_progress, best_event_score
        )

        # Early stop when best-score threshold is met
        if current_score >= BEST_FLOOR_PLAN_SCORE:
            print(
                f"[SolverLoop] early-stop pass: score={current_score:.2f} "
                f">= threshold={BEST_FLOOR_PLAN_SCORE:.2f}"
            )
            SystemLogger.log_event(
                tag="SOLVER",
                event="solver_best_early_stop",
                level="INFO",
                data={"score": current_score, "threshold": BEST_FLOOR_PLAN_SCORE},
            )
            return current_result

        SystemLogger.log_event(
            tag="SOLVER",
            event="solver_low_score",
            level="INFO",
            data={
                "attempt": attempt_index + 1,
                "score": current_score,
                "status": current_result.status,
            },
        )

        if current_score > best_score:
            best_score = current_score
            best_result = current_result

    if best_result is not None:
        return best_result
    if last_result is not None:
        return last_result

    return FpgEvaluationResult(
        solved=False,
        status="NO_RUN_ATTEMPTS",
        message="Inner solver loop did not execute any attempts.",
    )


def run_fpg_pipeline_api(
    floor_width: int,
    floor_height: int,
    aspect_ratio: float,
    room_template: RoomSetupTemplateBase,
    should_optuna_run: bool = False,
    optuna_trial_count: int = DEFAULT_OPTUNA_TRIALS,
    verbose: bool = True,
    progress_emitter: Callable[[str, str, dict[str, Any] | None], None] | None = None,
) -> dict[str, Any]:
    print("\nSTART: run_fpg_pipeline_api() ------")
    SystemLogger.log_event(
        tag="TEST",
        event="test_logs",
        level="INFO",
        data={"status": "working"},
    )

    def emit_progress(
        event: str, message: str, data: dict[str, Any] | None = None
    ) -> None:
        if progress_emitter is None:
            return
        try:
            progress_emitter(event, message, data)
        except Exception:
            return

    try:
        # Step 1: Build requirements
        requirements = build_requirements(
            floor_width=floor_width,
            floor_height=floor_height,
            aspect_ratio=aspect_ratio,
            room_template=room_template,
        )
        debug_log_data(requirements, "INITIAL_REQUIREMENTS")
        print(f"\n DATA DEBUG :\n After Build Requirements = {requirements}")

        # Step 2: Validate floor dimensions (Will Throw an Exception if invalid)
        validate_and_compute_floor_bounds(
            floor_width=floor_width,
            floor_height=floor_height,
            requirements=requirements,
        )

        # Step 3: Run solver
        if should_optuna_run:
            optuna_result = run_optuna_optimization(
                base_requirements=requirements,
                evaluator=lambda req, run_verbose: run_solver_with_hints(
                    requirements=req,
                    verbose=run_verbose,
                    run_count=FPG_SOLVER_RUN_COUNT,
                    progress_emitter=emit_progress,
                ),
                n_trials=optuna_trial_count,
                study_name=DEFAULT_OPTUNA_STUDY_NAME,
                storage=(
                    DEFAULT_OPTUNA_STORAGE_URL
                    if DEFAULT_OPTUNA_STORAGE_ENABLED
                    else None
                ),
                progress_emitter=emit_progress,
            )
            run_result = (
                optuna_result.best_run
                if optuna_result.best_run is not None
                else FpgEvaluationResult(
                    solved=False,
                    status="NO_BEST_RUN",
                    message="Optuna did not produce a best run.",
                )
            )
            termination_reason = optuna_result.termination_reason
        else:
            run_result = run_solver_with_hints(
                requirements=requirements,
                verbose=verbose,
                run_count=1,
                progress_emitter=emit_progress,
            )
            termination_reason = (
                "generation_success" if run_result.solved else "generation_failed"
            )

        # Plot the final solver result via public plotter API before payload construction
        try:
            plot_final_solver_result(run_result, show=False)
        except Exception as e:
            print(f"Failed to plot final solver result: {e}")

        SystemLogger.log_event(
            tag="SOLVER",
            event="solver_run_complete",
            level="INFO",
            data={"status": run_result.status, "solved": run_result.solved},
        )

        run_score = _extract_score(run_result)
        payload: dict[str, Any]
        if run_score is not None and run_score >= MINIMUM_REQUIRED_FPG_SCORE:
            payload = _build_result_payload(run_result, run_score)
        else:
            if should_optuna_run:
                if termination_reason == "generation_time_out":
                    failure_reason = "time_out"
                elif termination_reason == "trial_count_exceeded":
                    failure_reason = "trial_count_exceeded"
                else:
                    failure_reason = "system_error"
            else:
                failure_reason = "trial_count_exceeded"
            payload = _build_failure_payload(failure_reason)

        final_event = {
            "event": termination_reason,
            "message": payload.get("message", "Job finished."),
            "data": {
                "termination_reason": termination_reason,
                "result": payload,
            },
        }

        emit_progress(
            final_event["event"],
            final_event["message"],
            final_event["data"],
        )
        return payload

    except Exception as exc:
        error_message = f"Failed to generate layout: {exc}"
        print(f"\n ERROR: {error_message}")
        return _build_failure_payload(
            "system_error", message=error_message, details=str(exc)
        )

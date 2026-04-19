import contextlib
import io
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any

from app.algorithms.fpg_opening import generate_openings
from app.algorithms.fpg_rooms import FloorPlanGenerator
from app.algorithms.fpg_rooms.fpg_optuna import (
    FpgEvaluationResult,
    run_optuna_optimization,
)
from app.algorithms.fpg_rooms.fpg_post_process import (
    run_final_post_process,
    run_quick_post_process,
)
from app.util.logger.system_logger import SystemLogger

from app.algorithms.fpg_rooms.fpg_score import score_layout
from app.algorithms.fpg_rooms.fpgr_p_refine_1 import run_refine_profile_1
from app.algorithms.fpg_rooms.types.room import FpgRequirements
from app.core.fpg_rooms.config_fpg import (
    DEFAULT_OPTUNA_STUDY_NAME,
    DEFAULT_OPTUNA_STORAGE_ENABLED,
    DEFAULT_OPTUNA_STORAGE_URL,
    DEFAULT_OPTUNA_TRIALS,
    WIGGLE_ROOM,
)
from app.schemas.db.room_setup_template import RoomSetupTemplateBase
from app.util.algorithm_manager import (
    build_requirements,
    error_payload,
    validate_and_compute_floor_bounds,
)
from test.dev.final_result_plotter import plot_final_solver_result

EMPTY_POST_PROCESS_LAYOUT = {
    "union_walls": [],
    "rooms": {},
    "doors": [],
    "windows": [],
}
EMPTY_OPENING_LAYOUT = {
    "openings": [],
    "warnings": [],
    "status": "NOT_RUN",
    "message": "Not run",
}


def _plot_refine_before_after_dev(
    stage1_rooms: list[dict[str, Any]],
    stage2_rooms: list[dict[str, Any]],
    stage3_rooms: list[dict[str, Any]],
) -> str | None:
    """Best-effort dev-only plotting hook with zero impact on pipeline outcomes."""
    try:
        project_root = Path(__file__).resolve().parents[2]
        plotter_path = (
            project_root / "test" / "dev" / "fpgr_refine_debug" / "plotter.py"
        )
        if not plotter_path.exists():
            return None

        spec = spec_from_file_location("fpgr_refine_debug_plotter", plotter_path)
        if not spec or not spec.loader:
            return None

        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        plot_fn = getattr(module, "plot_refine_three_generations", None)
        if not callable(plot_fn):
            plot_fn = getattr(module, "plot_refine_before_after", None)
        if not callable(plot_fn):
            return None

        # Prefer 3-stage plotting if available, otherwise fallback to 2-stage
        output_dir = project_root / "test" / "outputs" / "refinements"
        output_dir.mkdir(parents=True, exist_ok=True)

        if plot_fn.__name__ == "plot_refine_three_generations":
            return plot_fn(
                before_rooms=stage1_rooms,
                middle_rooms=stage2_rooms,
                after_rooms=stage3_rooms,
                output_dir=output_dir,
                show=False,
            )

        return plot_fn(
            before_rooms=stage1_rooms,
            after_rooms=stage3_rooms,
            output_dir=output_dir,
            show=False,
        )
    except Exception:
        return None


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

    if not solved:
        print("\nNOT solved")
        return FpgEvaluationResult(
            solved=False,
            solution=[],
            score_report=None,
            status=status,
            message="Solver did not return FEASIBLE/OPTIMAL",
        )

    solution = generator.get_solution()
    print("\n get solution ")
    quick_post_process_result = run_quick_post_process(
        {"rooms": solution, "openings": []}
    )
    print("\n run quick post process")
    stage1_rooms = quick_post_process_result["rooms"]
    refine_result1 = run_refine_profile_1(
        requirements=requirements,
        initial_rooms=stage1_rooms,
        wiggle_room=WIGGLE_ROOM,
        verbose=False,
    )
    print("\n run_refine_profile_1")
    stage2_rooms = refine_result1.rooms if refine_result1.rooms else stage1_rooms
    refine_result2 = run_refine_profile_1(
        requirements=requirements,
        initial_rooms=stage2_rooms,
        wiggle_room=WIGGLE_ROOM,
        verbose=False,
    )
    print("\n run_refine_profile_2")
    stage3_rooms = refine_result2.rooms if refine_result2.rooms else stage2_rooms
    final_rooms = stage3_rooms
    _plot_refine_before_after_dev(
        stage1_rooms=stage1_rooms,
        stage2_rooms=stage2_rooms,
        stage3_rooms=stage3_rooms,
    )

    # Combined status/message from two refine passes for diagnostics
    refine_status = f"{refine_result1.status} -> {refine_result2.status}"
    refine_message = (
        f"Refine pass 1: {refine_result1.message}; "
        f"Refine pass 2: {refine_result2.message}"
    )

    final_quick_post_process_result = run_quick_post_process(
        {"rooms": final_rooms, "openings": []}
    )
    print("\n run_quick_post_process")

    opening_result = generate_openings(final_rooms)
    scoring_input = {
        **final_quick_post_process_result,
        "openings": opening_result.get("openings", []),
    }

    score_report = score_layout(
        solution=final_rooms,
        quick_post_process_result=scoring_input,
        requirements=requirements,
    )
    print("\n Score Layout")

    result = FpgEvaluationResult(
        solved=True,
        solution=final_rooms,
        score_report=score_report,
        status=status,
        message="Solver found a layout",
    )
    result.quick_post_process_result = scoring_input
    result.opening_result = opening_result
    result.refine_status = refine_status
    result.refine_message = refine_message
    return result


def _select_solver_result(
    requirements: FpgRequirements,
    should_optuna_run: bool,
    optuna_trial_count: int,
    verbose: bool,
) -> FpgEvaluationResult:
    print("\n _select_solver_result()")
    if not should_optuna_run:
        return _run_single_fpg_solve(requirements, verbose=verbose)

    optuna_result = run_optuna_optimization(
        base_requirements=requirements,
        evaluator=_run_single_fpg_solve,
        n_trials=optuna_trial_count,
        study_name=DEFAULT_OPTUNA_STUDY_NAME,
        storage=DEFAULT_OPTUNA_STORAGE_URL if DEFAULT_OPTUNA_STORAGE_ENABLED else None,
    )
    if optuna_result.best_run is not None:
        return optuna_result.best_run

    return FpgEvaluationResult(
        solved=False,
        solution=[],
        score_report=None,
        status="NO_BEST_RUN",
        message="Optuna did not produce a best run",
    )


def _build_payload_from_solver_result(
    run_result: FpgEvaluationResult,
) -> dict[str, Any]:
    print("\n _build_payload_from_solver_results()")
    if run_result.solved:
        quick_post_process_result = getattr(
            run_result, "quick_post_process_result", None
        )
        if quick_post_process_result is not None:
            post_processed_layout = quick_post_process_result["rooms"]
            wall_union_result = quick_post_process_result["wall_union"]
        else:
            post_processed_layout = run_result.solution
            wall_union_result = {"walls": [], "room_walls": {}}

        opening_result = getattr(run_result, "opening_result", None)
        if not isinstance(opening_result, dict):
            maybe_openings = (
                quick_post_process_result.get("openings")
                if quick_post_process_result
                else None
            )
            if isinstance(maybe_openings, list):
                opening_result = {
                    "status": "FROM_TRIAL",
                    "message": "Openings generated during scoring trial",
                    "openings": maybe_openings,
                    "warnings": [],
                }
            else:
                opening_result = generate_openings(post_processed_layout)

        post_process_result = run_final_post_process(
            {
                "rooms": post_processed_layout,
                "openings": opening_result.get("openings", []),
                "wall_union": wall_union_result,
            }
        )
    else:
        post_process_result = EMPTY_POST_PROCESS_LAYOUT

    return {
        "status": run_result.status,
        "message": run_result.message,
        "union_walls": post_process_result["union_walls"],
        "rooms": post_process_result["rooms"],
        "doors": post_process_result["doors"],
        "windows": post_process_result["windows"],
    }


def run_fpg_pipeline_api(
    floor_width: int,
    floor_height: int,
    room_template: RoomSetupTemplateBase,
    should_optuna_run: bool = False,
    optuna_trial_count: int = DEFAULT_OPTUNA_TRIALS,
    verbose: bool = True,
) -> dict[str, Any]:
    """API pipeline: use caller dimensions/template, fetch constraints server-side, then solve.

    New flow:
    1. Build requirements (internally loads and prunes server-side constraints)
    2. Validate floor dimensions
    3. Run solver (single or Optuna-based)
    4. Build and return formatted payload

    Args:
        floor_width: Floor plan width (integer after rounding in router)
        floor_height: Floor plan height (integer after rounding in router)
        room_template: Room template from API request
        should_optuna_run: Whether to use Optuna optimization
        optuna_trial_count: Number of Optuna trials
        verbose: Verbosity flag

    Returns:
        Response dict with status, message, union_walls, rooms, doors, windows
    """
    print("\nSTART: run_fpg_pipeline_api() ------")
    SystemLogger.log_event(
        tag="TEST",
        event="test_logs",
        level="INFO",
        data={"status": "working"},
    )
    
    print(f"\n DATA DEBUG ::\n<Initial> Floor Width = {floor_width}, Floor Height = {floor_height}, Room Template = {room_template} ")

    try:
        # Step 1: Build requirements (loads and prunes internally)
        requirements = build_requirements(
            floor_width=floor_width,
            floor_height=floor_height,
            room_template=room_template,
        )
        print(f"\n DATA DEBUG :\n After Build Requirements = {requirements}")

        # Step 2: Validate floor dimensions
        validation_result = validate_and_compute_floor_bounds(
            floor_width=floor_width,
            floor_height=floor_height,
            requirements=requirements,
        )
        print(f"\n DATA DEBUG :\n Floor Validation = {validation_result} ")

        # Step 3: Run solver
        run_result = _select_solver_result(
            requirements=requirements,
            should_optuna_run=should_optuna_run,
            optuna_trial_count=optuna_trial_count,
            verbose=verbose,
        )

        # Plot the final solver result via public plotter API before payload construction
        try:
            plot_final_solver_result(run_result, show=False)
        except Exception:
            pass

        # Step 4: Build and return formatted payload
        payload = _build_payload_from_solver_result(run_result)
        return payload

    except Exception as exc:
        error_message = f"Failed to generate layout: {exc}"
        print(f"\n ERROR: {error_message}")
        return error_payload(error_message)

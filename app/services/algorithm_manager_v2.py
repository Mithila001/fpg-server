import contextlib
import io
from collections.abc import Mapping, Sequence
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any, cast
from dataclasses import asdict, is_dataclass
import time

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
    DEFAULT_OPTUNA_STORAGE_ENABLED,
    DEFAULT_OPTUNA_STORAGE_URL,
    WIGGLE_ROOM,
)
from app.algorithms.types.domain import ProcessedRoomData
from app.schemas.db.room_setup_template import RoomSetupTemplateBase
from app.util.algorithm_manager import (
    build_requirements,
    error_payload,
    validate_and_compute_floor_bounds,
)
from test.dev.final_result_plotter import plot_final_solver_result
from test.dev.plot_refiner import plot_refine_floor_plan


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

FPG_SOLVER_RUN_COUNT = 2


def _normalize_room_dicts(
    rooms: Sequence[Mapping[str, Any]] | Sequence[Any],
) -> list[dict[str, Any]]:
    return [dict(room) for room in rooms if isinstance(room, Mapping)]


def _plot_refine_before_after_dev(
    stage1_rooms: list[dict[str, Any]],
    stage2_rooms: list[dict[str, Any]],
    stage3_rooms: list[dict[str, Any]],
) -> str | None:
    """Best-effort dev-only plotting hook with zero impact on pipeline outcomes."""

    print(f"Stage1: {stage1_rooms}")
    print(f"Stage2: {stage2_rooms}")
    print(f"Stage3: {stage3_rooms}")
    try:
        project_root = Path(__file__).resolve().parents[2]
        plotter_path = (
            project_root / "test" / "dev" / "fpgr_refine_debug" / "plotter.py"
        )
        if not plotter_path.exists():
            # If this prints, the file literally isn't at the path above
            print(f"\n\n ERROR: Plotter not found at {plotter_path}\n\n")
            return None

        spec = spec_from_file_location("fpgr_refine_debug_plotter", plotter_path)
        if not spec or not spec.loader:
            print("\n\n 22\n\n")
            return None

        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        plot_fn: Any = getattr(module, "plot_refine_three_generations", None)
        if not callable(plot_fn):
            print("\n\n 33\n\n")
            plot_fn = getattr(module, "plot_refine_before_after", None)
        if not callable(plot_fn):
            print("\n\n 44\n\n")
            return None

        # Prefer 3-stage plotting if available, otherwise fallback to 2-stage

        output_dir = project_root / "test" / "outputs" / "refine"
        output_dir.mkdir(parents=True, exist_ok=True)

        if plot_fn.__name__ == "plot_refine_three_generations":
            return cast(
                str | None,
                plot_fn(
                    before_rooms=stage1_rooms,
                    middle_rooms=stage2_rooms,
                    after_rooms=stage3_rooms,
                    output_dir=output_dir,
                    show=False,
                ),
            )

        return cast(
            str | None,
            plot_fn(
                before_rooms=stage1_rooms,
                after_rooms=stage3_rooms,
                output_dir=output_dir,
                show=False,
            ),
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
    print(f"Status:{status}")

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
    stage1_rooms = _normalize_room_dicts(quick_post_process_result["rooms"])

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
    stage4_rooms = refine_result3.rooms if refine_result3.rooms else stage3_rooms

    # --- PASS 4: Standard Refine ---
    refine_result4 = run_refine_profile_1(
        requirements=requirements,
        initial_rooms=stage4_rooms,
        wiggle_room=WIGGLE_ROOM,
        verbose=False,
    )
    print("\n run_refine_profile_4 (Pass 4)")
    stage5_rooms = refine_result4.rooms if refine_result4.rooms else stage4_rooms

    # --- PASS 5: Standard Refine ---
    refine_result5 = run_refine_profile_1(
        requirements=requirements,
        initial_rooms=stage5_rooms,
        wiggle_room=WIGGLE_ROOM,
        verbose=False,
    )
    print("\n run_refine_profile_5 (Pass 5)")
    final_rooms = refine_result5.rooms if refine_result5.rooms else stage5_rooms

    plot_refine_floor_plan(
        stage1_rooms=stage1_rooms, stage2_rooms=stage2_rooms, stage4_rooms=final_rooms
    )
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

    fpg_score_results: ScoreManagerResult | int = score_manager(
        floor_plan_with_openings, requirements
    )
    union_results: UnionFloorPlanResult = union_floor_plan(floor_plan_with_openings)

    # print(f"\n union_results : {union_results}\n")

    # Combined status/message from refine passes for diagnostics
    refine_status = (
        f"{refine_result1.status} -> {refine_result2.status} -> "
        f"{refine_result3.status} -> {refine_result4.status} -> {refine_result5.status}"
    )
    refine_message = (
        f"Refine pass 1: {refine_result1.message}; "
        f"Refine pass 2: {refine_result2.message}; "
        f"Refine pass 3: {refine_result3.message}; "
        f"Refine pass 4: {refine_result4.message}; "
        f"Refine pass 5: {refine_result5.message}"
    )

    result = FpgEvaluationResult(
        solved=True,
        solution=final_rooms,
        score_report=None,
        status=status,
        message="Solver found a layout",
    )
    # Attach the newer artifacts produced earlier in this function
    result.fpg_score_results = fpg_score_results
    result.union_results = union_results
    try:
        if is_dataclass(floor_plan_with_openings):
            result.floor_plan_with_openings = asdict(floor_plan_with_openings)
        else:
            result.floor_plan_with_openings = cast(
                dict[str, Any], getattr(floor_plan_with_openings, "__dict__", None)
            )
    except Exception:
        result.floor_plan_with_openings = None

    result.refine_status = refine_status
    result.refine_message = refine_message
    return result


def run_solver_with_hints(
    requirements: FpgRequirements,
    verbose: bool = True,
    run_count: int = FPG_SOLVER_RUN_COUNT,
) -> FpgEvaluationResult:
    """Inner loop for Phase 3: repeatedly run solver with point hints and keep best solved layout."""
    safe_run_count = max(1, int(run_count))

    best_result: FpgEvaluationResult | None = None
    best_score = float("-inf")
    last_result: FpgEvaluationResult | None = None

    # TODO: Remove hallways from Hint DEBUG
    # requirements.initial_point_hints = [
    #     hint
    #     for hint in requirements.initial_point_hints
    #     if hint.get("type") != "hallway"
    # ]
    print(f"\nUpdated Hints: {requirements.initial_point_hints}\n")
    print(f"[SolverLoop] safe_run_count: {safe_run_count}\n")
    for attempt_index in range(safe_run_count):
        current_result = _run_single_fpg_solve(
            requirements=requirements, verbose=verbose
        )
        print(
            f"\n[SolverLoop] Current Result Score Attempt {attempt_index + 1}: {current_result.fpg_score_results}\n"
        )
        last_result = current_result
        if not current_result.solved or current_result.score_report is None:
            print(
                f"[SolverLoop] attempt={attempt_index + 1}/{safe_run_count} "
                f"status={current_result.status} solved={current_result.solved}"
            )
            continue

        # Prefer new `fpg_score_results` critical score when available, otherwise fall back
        # to the legacy `score_report.total_score`.
        current_score = None
        fpg_score = getattr(current_result, "fpg_score_results", None)
        print(f"[SolverLoop] fpg_score: {fpg_score}\n")
        if fpg_score is not None:
            try:
                # ScoreManagerResult has `critical_score` attribute
                current_score = float(getattr(fpg_score, "critical_score", fpg_score))
            except Exception:
                current_score = None
        if (
            current_score is None
            and getattr(current_result, "score_report", None) is not None
        ):
            try:
                current_score = float(current_result.score_report.total_score)
            except Exception:
                current_score = None
        if current_score is None:
            print(
                f"[SolverLoop] attempt={attempt_index + 1}/{safe_run_count} missing score, skipping"
            )
            continue
        print(
            f"[SolverLoop] attempt={attempt_index + 1}/{safe_run_count} "
            f"status={current_result.status} score={current_score:.2f}"
        )

        if current_score >= MINIMUM_REQUIRED_FPG_SCORE:
            print(
                f"[SolverLoop] early-stop pass: score={current_score:.2f} "
                f">= threshold={MINIMUM_REQUIRED_FPG_SCORE:.2f}"
            )
            SystemLogger.log_event(
                tag="SOLVER",
                event="solver_early_stop",
                level="INFO",
                data={
                    "score": current_score,
                    "threshold": MINIMUM_REQUIRED_FPG_SCORE,
                },
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
        solution=[],
        score_report=None,
        status="NO_RUN_ATTEMPTS",
        message="Inner solver loop did not execute any attempts.",
    )


def _build_payload_from_solver_result(
    run_result: FpgEvaluationResult,
) -> dict[str, Any]:
    print("\n _build_payload_from_solver_results()")

    # Always include status and message from run_result
    base_payload = {
        "status": run_result.status,
        "message": run_result.message,
        "union_walls": [],
        "unified_floor_plan": None,
        "floor_plan_with_openings": None,
        "rooms": {},
        "doors": [],
        "windows": [],
    }

    if not run_result.solved:
        return base_payload

    # New flow: use union_results and floor_plan_with_openings for payload
    union_results_obj = getattr(run_result, "union_results", None)
    if not union_results_obj:
        return base_payload

    try:
        unified_floor_plan = union_results_obj.get("unified_floor_plan")
        floor_plan_with_openings_obj = union_results_obj.get("floor_plan_with_openings")
    except (KeyError, TypeError, AttributeError):
        return base_payload

    if not unified_floor_plan or not floor_plan_with_openings_obj:
        return base_payload

    # Extract walls from unified floor plan
    union_walls = unified_floor_plan.get("walls", [])

    # Extract openings and rooms from floor_plan_with_openings
    floor_plan = getattr(
        floor_plan_with_openings_obj, "floor_plan", None
    ) or floor_plan_with_openings_obj.get("floor_plan", [])
    openings = getattr(
        floor_plan_with_openings_obj, "openings", None
    ) or floor_plan_with_openings_obj.get("openings", [])

    # Build rooms dictionary from floor_plan
    rooms = {}
    for room in floor_plan or []:
        room_dict = _to_dict(room) if not isinstance(room, dict) else room
        room_name = room_dict.get("name", "unknown")
        room_type = room_dict.get("type", "generic")
        rooms[room_name] = {
            "room_name": room_name,
            "room_type": room_type,
            "room_walls": [],  # Walls already unified in union_walls
        }

    # Separate doors and windows from openings
    doors = []
    windows = []
    for opening in openings or []:
        opening_dict = _to_dict(opening) if not isinstance(opening, dict) else opening
        opening_type = opening_dict.get("opening_type", "door")
        if "window" in opening_type.lower():
            windows.append(opening_dict)
        else:
            doors.append(opening_dict)

    return {
        "status": run_result.status,
        "message": run_result.message,
        "union_walls": union_walls,
        "unified_floor_plan": unified_floor_plan,
        "floor_plan_with_openings": floor_plan_with_openings_obj,
        "rooms": rooms,
        "doors": doors,
        "windows": windows,
    }


def _to_dict(value: Any) -> dict[str, Any]:
    """Normalize dataclasses into plain dictionaries."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return cast(dict[str, Any], model_dump())
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return {}


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
    print(
        f"\n DATA DEBUG ::\n<Initial> Floor Width = {floor_width}, Floor Height = {floor_height}, Room Template = {room_template} "
    )

    try:
        # Step 1: Build requirements (loads and prunes internally)
        requirements = build_requirements(
            floor_width=floor_width,
            floor_height=floor_height,
            room_template=room_template,
        )
        debug_log_data(requirements, "INITIAL_REQUIREMENTS")
        print(f"\n DATA DEBUG :\n After Build Requirements = {requirements}")

        # Step 2: Validate floor dimensions (Will Throw an Exception)
        validate_and_compute_floor_bounds(
            floor_width=floor_width,
            floor_height=floor_height,
            requirements=requirements,
        )
        #  Load Size Constraints

        # Step 3: Run solver
        if should_optuna_run:
            optuna_result = run_optuna_optimization(
                base_requirements=requirements,
                evaluator=lambda req, run_verbose: run_solver_with_hints(
                    requirements=req,
                    verbose=run_verbose,
                    run_count=FPG_SOLVER_RUN_COUNT,
                ),
                n_trials=optuna_trial_count,
                study_name=DEFAULT_OPTUNA_STUDY_NAME,
                storage=(
                    DEFAULT_OPTUNA_STORAGE_URL
                    if DEFAULT_OPTUNA_STORAGE_ENABLED
                    else None
                ),
            )
            run_result = (
                optuna_result.best_run
                if optuna_result.best_run is not None
                else FpgEvaluationResult(
                    solved=False,
                    solution=[],
                    score_report=None,
                    status="NO_BEST_RUN",
                    message="Optuna did not produce a best run.",
                )
            )
        else:
            run_result = _run_single_fpg_solve(
                requirements=requirements,
                verbose=verbose,
            )

        # Plot the final solver result via public plotter API before payload construction
        try:
            plot_final_solver_result(run_result, show=False)
        except Exception:
            pass

            SystemLogger.log_event(
                tag="SOLVER",
                event="solver_run_complete",
                level="INFO",
                data={"status": run_result.status, "solved": run_result.solved},
            )
        # Step 4: Build and return formatted payload
        payload = _build_payload_from_solver_result(run_result)
        return payload

    except Exception as exc:
        error_message = f"Failed to generate layout: {exc}"
        print(f"\n ERROR: {error_message}")
        return error_payload(error_message)

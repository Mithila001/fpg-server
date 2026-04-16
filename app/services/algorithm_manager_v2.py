import contextlib
import io
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any, Sequence

from sqlmodel import Session

from app.algorithms.fpg_opening import generate_openings
from app.algorithms.fpg_rooms import FloorPlanGenerator
from app.algorithms.fpg_rooms.fpg_optuna import (
    FpgEvaluationResult,
    OptunaOptimizationResult,
    run_optuna_optimization,
)
from app.algorithms.fpg_rooms.fpg_post_process import (
    run_final_post_process,
    run_quick_post_process,
)
from app.util.logger.system_logger import SystemLogger

from app.algorithms.fpg_rooms.fpg_score import score_layout
from app.algorithms.fpg_rooms.fpgr_p_refine_1 import run_refine_profile_1
from app.algorithms.fpg_rooms.types.room import ConfigData, FpgRequirements, RoomData
from app.core.database import engine
from app.core.fpg_rooms.config_fpg import (
    DEFAULT_ASPECT_RATIO_MAX,
    DEFAULT_ASPECT_RATIO_MIN,
    DEFAULT_HALLWAY_COUNT,
    DEFAULT_MAX_H,
    DEFAULT_MAX_W,
    DEFAULT_MIN_H,
    DEFAULT_MIN_W,
    DEFAULT_OPTUNA_STORAGE_ENABLED,
    DEFAULT_OPTUNA_STORAGE_URL,
    DEFAULT_OPTUNA_TRIALS,
    ENVELOPE_APPLY_SIDES,
    ENVELOPE_ENABLED,
    ENVELOPE_EXCLUDE_TYPES,
    ENVELOPE_MAX_GAP,
    ENVELOPE_MIN_GAP,
    MIN_COVERAGE,
    MIN_FLOOR_WIDTH,
    MIN_FLOOR_HEIGHT,
    MIN_FLOOR_AREA_BUFFER,
    WIGGLE_ROOM,
    DEFAULT_OPTUNA_STUDY_NAME
)
from app.crud import (
    room_relations_constraint as room_relations_constraint_crud,
    room_setup_template as room_setup_template_crud,
    room_size_constraint as room_size_constraint_crud,
)
from app.schemas.db.room_setup_template import RoomSetupTemplateBase
from app.util.dev_use_mock_db import (
    load_room_relations_constraints,
    load_room_setup_templates,
    load_room_size_constraints,
)
from app.util.constraint_pruner import prune_room_relations_constraints_by_template
from app.util.room_requirements import (
    normalize_db_data_requirements,
)
from test.dev.final_result_plotter import plot_final_solver_result

EMPTY_POST_PROCESS_LAYOUT = {
    "walls": [],
    "compact_by_room": {},
    "metadata": {
        "veranda": None,
        "garage_shared_horizontal_overlap_segment": None,
        "hallway_living_shared_walls": [],
        "converted_hallway_living_openings": 0,
    },
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
        plotter_path = project_root / "test" / "dev" / "fpgr_refine_debug" / "plotter.py"
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
        if plot_fn.__name__ == "plot_refine_three_generations":
            return plot_fn(
                before_rooms=stage1_rooms,
                middle_rooms=stage2_rooms,
                after_rooms=stage3_rooms,
                show=False,
            )

        return plot_fn(before_rooms=stage1_rooms, after_rooms=stage3_rooms, show=False)
    except Exception:
        return None


def _error_payload(message: str, status: str = "ERROR") -> dict[str, Any]:
    return {
        "status": status,
        "message": message,
        "walls": [],
        "compact_by_room": {},
        "metadata": EMPTY_POST_PROCESS_LAYOUT["metadata"],
    }


def _load_server_side_data() -> tuple[list[Any], Sequence[Any], Sequence[Any]]:
    """Load templates, size constraints and relation constraints from server side source.

    During development this mirrors existing manager behavior by using mock JSON data.
    """
    print("\nSTART: _load_server_side_data ------")
    should_bypass = True

    if should_bypass:
        templates = load_room_setup_templates()
        size_constraints = load_room_size_constraints()
        relation_constraints = load_room_relations_constraints()
        return templates, size_constraints, relation_constraints

    with Session(engine) as session:
        templates = room_setup_template_crud.get_all(session)
        size_constraints = room_size_constraint_crud.get_all(session)
        relation_constraints = room_relations_constraint_crud.get_all(session)
    
    return templates, size_constraints, relation_constraints


def _build_rooms_from_template(template: RoomSetupTemplateBase) -> list[RoomData]:
    rooms: list[RoomData] = []
    for entry in template.data:
        room_type = entry.get("type", "")
        room_name = entry.get("name") or entry.get("id") or room_type
        rooms.append(
            RoomData(
                name=room_name,
                type=room_type,
                min_w=DEFAULT_MIN_W,
                min_h=DEFAULT_MIN_H,
                max_w=DEFAULT_MAX_W,
                max_h=DEFAULT_MAX_H,
            )
        )
    return rooms




def _build_requirements(
    floor_width: float,
    floor_height: float,
    room_template: RoomSetupTemplateBase,
) -> FpgRequirements:
    """Build FpgRequirements from template, loading and pruning server-side constraints.
    
    This function now handles all data loading and constraint pruning internally.
    Raises exceptions if any step fails (no silent defaults).
    
    Args:
        floor_width: Floor plan width
        floor_height: Floor plan height
        room_template: Room template from API request
        
    Returns:
        FpgRequirements with all constraints loaded and pruned
        
    Raises:
        Exception: If server-side data loading or pruning fails
    """
    print("\n _build_requirements()")
    
    # Step 1: Load server-side data (with separate try-catch for clarity)
    try:
        _, size_constraints, relation_constraints = _load_server_side_data()
    except Exception as exc:
        raise Exception(
            f"Failed to load server-side constraints: {exc}"
        ) from exc
    
    # Step 2: Prune room relations constraints by template (with separate try-catch)
    try:
        relation_constraints, prune_error = prune_room_relations_constraints_by_template(
            room_template=room_template,
            room_relations_constraints=relation_constraints,
        )
        if prune_error:
            raise Exception(f"Failed to prune relation constraints: {prune_error}")
    except Exception as exc:
        raise Exception(
            f"Failed to prune room relations constraints: {exc}"
        ) from exc
    
    # Step 3: Build and normalize rooms from template
    rooms = _build_rooms_from_template(room_template)
    normalized_rooms = normalize_db_data_requirements(rooms, size_constraints)

    config = ConfigData(
        min_coverage=MIN_COVERAGE,
        max_aspect_ratio=DEFAULT_ASPECT_RATIO_MAX,
        min_aspect_ratio=DEFAULT_ASPECT_RATIO_MIN,
        floor_plan_width=floor_width,
        floor_plan_height=floor_height,
        hallway_count=DEFAULT_HALLWAY_COUNT,
        envelope_enabled=ENVELOPE_ENABLED,
        envelope_min_gap=ENVELOPE_MIN_GAP,
        envelope_max_gap=ENVELOPE_MAX_GAP,
        envelope_exclude_types=ENVELOPE_EXCLUDE_TYPES,
        envelope_apply_sides=ENVELOPE_APPLY_SIDES,
    )
    return FpgRequirements(
        rooms=normalized_rooms,
        config=config,
        relation_constraints=list(relation_constraints),
    )


def _validate_and_compute_floor_bounds(
    floor_width: int,
    floor_height: int,
    requirements: FpgRequirements,
) -> dict[str, Any]:
    """Validate floor dimensions and compute bounds for Optuna.
    
    Performs comprehensive validation:
    1. Check minimum floor dimensions
    2. Verify sufficient area for all rooms + buffer
    3. Validate aspect ratio within supported range
    4. Compute and return min/max floor dimension bounds
    
    Args:
        floor_width: Floor plan width
        floor_height: Floor plan height
        requirements: FpgRequirements with room constraints
        
    Returns:
        Dict with keys: status, message, min_floor_width, min_floor_height,
        max_floor_width, max_floor_height, floor_aspect_ratio
        
    Raises:
        Exception: If validation fails at any step
    """
    import math
    
    print("\n _validate_and_compute_floor_bounds()")
    
    # Step 1: Check minimum floor dimensions
    if floor_width < MIN_FLOOR_WIDTH or floor_height < MIN_FLOOR_HEIGHT:
        raise Exception(
            f"Floor dimensions are too small. "
            f"Received: {floor_width} x {floor_height}, "
            f"Minimum required: {MIN_FLOOR_WIDTH} x {MIN_FLOOR_HEIGHT}"
        )
    
    # Step 2: Verify sufficient area for all rooms + buffer
    total_min_area = 0.0
    for room in requirements.rooms:
        min_w = getattr(room, "min_w", None)
        min_h = getattr(room, "min_h", None)
        
        if min_w is None or min_h is None:
            raise Exception(
                f"Room '{getattr(room, 'name', '<unknown>')}' has missing min dimensions"
            )
        
        try:
            total_min_area += float(min_w) * float(min_h)
        except (TypeError, ValueError):
            raise Exception(
                f"Room '{getattr(room, 'name', '<unknown>')}' has invalid dimensions"
            )
    
    # Add buffer to minimum required area
    total_min_area_with_buffer = total_min_area + MIN_FLOOR_AREA_BUFFER
    floor_area = float(floor_width) * float(floor_height)
    
    if total_min_area_with_buffer > floor_area:
        shortage = total_min_area_with_buffer - floor_area
        raise Exception(
            f"Insufficient floor area. Total minimum room area + buffer = "
            f"{total_min_area:.2f} + {MIN_FLOOR_AREA_BUFFER} = {total_min_area_with_buffer:.2f}, "
            f"but floor area = {floor_width} × {floor_height} = {floor_area:.2f}. "
            f"Shortage: {shortage:.2f} square units."
        )
    
    # Step 3: Compute aspect ratio and bounds
    floor_aspect_ratio = floor_width / floor_height if floor_height > 0 else 1.0
    
    # The supported aspect ratio range is 1:1 (square) to 16:9 (wide rectangle)
    # Compute normalized aspect ratio
    normalized_aspect = max(1.0, floor_aspect_ratio)
    
    # Compute floor dimension min/max bounds
    # Min bound: based on minimum room areas
    min_floor_area = total_min_area
    min_floor_width = math.sqrt(min_floor_area * normalized_aspect)
    min_floor_height = min_floor_width / normalized_aspect if normalized_aspect > 0 else min_floor_width
    
    # Max bound: limited by provided floor dimensions
    max_floor_width = float(floor_width)
    max_floor_height = float(floor_height)
    
    return {
        "status": "OK",
        "message": "Floor dimensions validated successfully",
        "min_floor_width": int(math.floor(min_floor_width)),
        "min_floor_height": int(math.floor(min_floor_height)),
        "max_floor_width": int(max_floor_width),
        "max_floor_height": int(max_floor_height),
        "floor_aspect_ratio": floor_aspect_ratio,
    }


def _run_single_fpg_solve(
    requirements: FpgRequirements,
    verbose: bool = True,
) -> FpgEvaluationResult:
    generator = FloorPlanGenerator(requirements)
    print("\n _run_single_fpg_solve")
    
    verbose= False # TODO DEBUG FLAG Remove this 
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
    quick_post_process_result = run_quick_post_process({"rooms": solution, "openings": []})
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
    # _plot_refine_before_after_dev(
    #     stage1_rooms=stage1_rooms,
    #     stage2_rooms=stage2_rooms,
    #     stage3_rooms=stage3_rooms,
    # )

    # Combined status/message from two refine passes for diagnostics
    refine_status = f"{refine_result1.status} -> {refine_result2.status}"
    refine_message = (
        f"Refine pass 1: {refine_result1.message}; "
        f"Refine pass 2: {refine_result2.message}"
    )

    final_quick_post_process_result = run_quick_post_process({"rooms": final_rooms, "openings": []})
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


def _run_optuna_entry(
    requirements: FpgRequirements,
    floor_dimension_bounds: dict[str, int],
    optuna_trial_count: int = DEFAULT_OPTUNA_TRIALS,
    study_name: str = "fpg_layout_optimization",
) -> OptunaOptimizationResult:
    """Run Optuna optimization with pre-computed floor dimension bounds.
    
    Args:
        requirements: FpgRequirements with room and constraint data
        floor_dimension_bounds: Pre-computed bounds dict with keys:
            min_floor_width, min_floor_height, max_floor_width, max_floor_height
        optuna_trial_count: Number of trials to run
        study_name: Name for Optuna study
        
    Returns:
        OptunaOptimizationResult with best trial information
    """
    storage = DEFAULT_OPTUNA_STORAGE_URL if DEFAULT_OPTUNA_STORAGE_ENABLED else None
    run_study_name = DEFAULT_OPTUNA_STUDY_NAME
    
    print("\n _run_optuna_entry() ")

    return run_optuna_optimization(
        base_requirements=requirements,
        evaluator=_run_single_fpg_solve,
        n_trials=optuna_trial_count,
        study_name=run_study_name,
        storage=storage,
        floor_dimension_bounds=floor_dimension_bounds,
    )



def _select_solver_result(
    requirements: FpgRequirements,
    floor_dimension_bounds: dict[str, int],
    should_optuna_run: bool,
    optuna_trial_count: int,
    verbose: bool,
) -> FpgEvaluationResult:
    print("\n _select_solver_result()")
    if not should_optuna_run:
        return _run_single_fpg_solve(requirements, verbose=verbose)

    optuna_result = _run_optuna_entry(
        requirements=requirements,
        floor_dimension_bounds=floor_dimension_bounds,
        optuna_trial_count=optuna_trial_count,
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


def _build_payload_from_solver_result(run_result: FpgEvaluationResult) -> dict[str, Any]:
    print("\n _build_payload_from_solver_results()")
    if run_result.solved:
        quick_post_process_result = getattr(run_result, "quick_post_process_result", None)
        if quick_post_process_result is not None:
            post_processed_layout = quick_post_process_result["rooms"]
            wall_union_result = quick_post_process_result["wall_union"]
        else:
            post_processed_layout = run_result.solution
            wall_union_result = {"walls": [], "room_walls": {}}

        opening_result = getattr(run_result, "opening_result", None)
        if not isinstance(opening_result, dict):
            maybe_openings = quick_post_process_result.get("openings") if quick_post_process_result else None
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
        "walls": post_process_result["walls"],
        "compact_by_room": post_process_result["compact_by_room"],
        "metadata": post_process_result.get("metadata", EMPTY_POST_PROCESS_LAYOUT["metadata"]),
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
    2. Validate floor dimensions and compute bounds
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
        Response dict with status, message, walls, compact_by_room, metadata
    """
    print("\nSTART: run_fpg_pipeline_api() ------")
    SystemLogger.log_event(
        tag="TEST",
        event="test_logs",
        level="INFO",
        data={"status": "working"},
    )

    try:
        # Step 1: Build requirements (loads and prunes internally)
        requirements = _build_requirements(
            floor_width=floor_width,
            floor_height=floor_height,
            room_template=room_template,
        )
        
        # Step 2: Validate floor dimensions and compute bounds
        bounds_result = _validate_and_compute_floor_bounds(
            floor_width=floor_width,
            floor_height=floor_height,
            requirements=requirements,
        )
        
        floor_dimension_bounds = {
            "min_floor_width": bounds_result["min_floor_width"],
            "min_floor_height": bounds_result["min_floor_height"],
            "max_floor_width": bounds_result["max_floor_width"],
            "max_floor_height": bounds_result["max_floor_height"],
        }
        
        # Step 3: Run solver with validated bounds
        run_result = _select_solver_result(
            requirements=requirements,
            floor_dimension_bounds=floor_dimension_bounds,
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
        return _error_payload(error_message)


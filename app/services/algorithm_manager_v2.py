import contextlib
import io
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from time import perf_counter
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
    FLOOR_HEIGHT,
    FLOOR_WIDTH,
    MIN_COVERAGE,
    SAFETY_BUFFER,
    WIGGLE_ROOM,
    DEFAULT_OPTUNA_STUDY_NAME
)
from app.crud import (
    room_relations_constraint as room_relations_constraint_crud,
    room_setup_template as room_setup_template_crud,
    room_size_constraint as room_size_constraint_crud,
)
from app.schemas.db.room_setup_template import RoomSetupTemplateBase
from app.schemas.db.room_size_constraints import RoomSizeConstraintBase
from app.util.dev_use_mock_db import (
    load_room_relations_constraints,
    load_room_setup_templates,
    load_room_size_constraints,
)
from app.util.logger import SystemLogger
from app.util.constraint_pruner import prune_room_relations_constraints_by_template
from app.util.room_requirements import (
    compute_floor_plan_dimension_bounds,
    normalize_db_data_requirements,
)
from test.dev.final_result_plotter import plot_final_solver_result

EMPTY_POST_PROCESS_LAYOUT = {"walls": [], "compact_by_room": {}}
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
    }


def _load_server_side_data() -> tuple[list[Any], Sequence[Any], Sequence[Any]]:
    """Load templates, size constraints and relation constraints from server side source.

    During development this mirrors existing manager behavior by using mock JSON data.
    """
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


def pre_validation(
    room_template: RoomSetupTemplateBase,
    room_size_constraints: Sequence[RoomSizeConstraintBase],
    floor_width: float,
    floor_height: float,
) -> tuple[bool, str | None]:
    """Validate template feasibility before solver execution.

    Rule: if total minimum room area + 100 exceeds floor area,
    the request is treated as impossible for the given floor size.
    """
    if floor_width <= 0 or floor_height <= 0:
        return False, "Floor width and height must be positive values."

    if room_template is None or not room_template.data:
        return False, "Room template data is empty."

    constraints_by_type = {c.type: c for c in room_size_constraints}
    total_min_area = 0.0

    for entry in room_template.data:
        room_type = entry.get("type")
        if not room_type:
            return False, "Room template contains an entry without room type."

        constraint = constraints_by_type.get(room_type)
        if constraint is None:
            return False, f"Missing room size constraint for room type: {room_type}"

        if constraint.min_area is not None:
            min_area = float(constraint.min_area)
        elif constraint.min_w is not None and constraint.min_h is not None:
            min_area = float(constraint.min_w) * float(constraint.min_h)
        else:
            return (
                False,
                f"Missing min area definition for room type: {room_type}",
            )

        total_min_area += min_area

    floor_area = float(floor_width) * float(floor_height)
    required_min_area = total_min_area + SAFETY_BUFFER

    if required_min_area > floor_area:
        shortage = required_min_area - floor_area
        return (
            False,
            "Impossible Requirements For the given floor area. "
            f"Required min area + buffer = {total_min_area:.2f} + {SAFETY_BUFFER:.2f} "
            f"= {required_min_area:.2f}, floor area = {floor_width:.2f} * {floor_height:.2f} "
            f"= {floor_area:.2f}, shortage = {shortage:.2f}.",
        )

    return True, None


def _build_requirements(
    floor_width: float,
    floor_height: float,
    room_template: RoomSetupTemplateBase,
    room_size_constraints: Sequence[Any],
    room_relations_constraints: Sequence[Any],
) -> FpgRequirements:
    rooms = _build_rooms_from_template(room_template)
    normalized_rooms = normalize_db_data_requirements(rooms, room_size_constraints)

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
        relation_constraints=list(room_relations_constraints),
    )


def _run_single_fpg_solve(
    requirements: FpgRequirements,
    verbose: bool = True,
) -> FpgEvaluationResult:
    generator = FloorPlanGenerator(requirements)

    if verbose:
        solved = generator.generate()
    else:
        with contextlib.redirect_stdout(io.StringIO()):
            solved = generator.generate()

    status = generator.last_status_name

    if not solved:
        return FpgEvaluationResult(
            solved=False,
            solution=[],
            score_report=None,
            status=status,
            message="Solver did not return FEASIBLE/OPTIMAL",
        )

    solution = generator.get_solution()
    quick_post_process_result = run_quick_post_process({"rooms": solution, "openings": []})

    stage1_rooms = quick_post_process_result["rooms"]

    refine_result1 = run_refine_profile_1(
        requirements=requirements,
        initial_rooms=stage1_rooms,
        wiggle_room=WIGGLE_ROOM,
        verbose=False,
    )
    stage2_rooms = refine_result1.rooms if refine_result1.rooms else stage1_rooms

    single_refine_mode = bool(
        getattr(requirements.config, "living_room_extender_single_refine_run", False)
    ) and bool(
        getattr(requirements.config, "living_room_extender_refine_only_enabled", False)
    )

    if single_refine_mode:
        refine_result2 = refine_result1
        stage3_rooms = stage2_rooms
    else:
        refine_result2 = run_refine_profile_1(
            requirements=requirements,
            initial_rooms=stage2_rooms,
            wiggle_room=WIGGLE_ROOM,
            verbose=False,
        )
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

    final_quick_post_process_result = run_quick_post_process({"rooms": final_rooms, "openings": []})

    score_report = score_layout(
        solution=final_rooms,
        quick_post_process_result=final_quick_post_process_result,
        requirements=requirements,
    )

    result = FpgEvaluationResult(
        solved=True,
        solution=final_rooms,
        score_report=score_report,
        status=status,
        message="Solver found a layout",
    )
    result.quick_post_process_result = final_quick_post_process_result
    result.refine_status = refine_status
    result.refine_message = refine_message
    return result


def _run_optuna_entry(
    requirements: FpgRequirements,
    optuna_trial_count: int = DEFAULT_OPTUNA_TRIALS,
    study_name: str = "fpg_layout_optimization",
) -> OptunaOptimizationResult:
    storage = DEFAULT_OPTUNA_STORAGE_URL if DEFAULT_OPTUNA_STORAGE_ENABLED else None
    # run_study_name = f"{study_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_study_name = DEFAULT_OPTUNA_STUDY_NAME

    bounds_result = compute_floor_plan_dimension_bounds(requirements)
    if bounds_result.get("status") != "OK":
        message = str(bounds_result.get("message") or "Failed to compute floor bounds")
        return OptunaOptimizationResult(
            study_name=run_study_name,
            best_value=0.0,
            best_trial_number=-1,
            best_params={},
            completed_trials=0,
            failed_trials=0,
            best_run=FpgEvaluationResult(
                solved=False,
                solution=[],
                score_report=None,
                status="INVALID_FLOOR_DIMENSION_BOUNDS",
                message=message,
            ),
        )

    floor_dimension_bounds = {
        "min_floor_width": int(float(bounds_result["min_floor_width"])),
        "min_floor_height": int(float(bounds_result["min_floor_height"])),
        "max_floor_width": int(float(bounds_result["max_floor_width"])),
        "max_floor_height": int(float(bounds_result["max_floor_height"])),
    }

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
    should_optuna_run: bool,
    optuna_trial_count: int,
    verbose: bool,
) -> FpgEvaluationResult:
    if not should_optuna_run:
        return _run_single_fpg_solve(requirements, verbose=verbose)

    optuna_result = _run_optuna_entry(
        requirements=requirements,
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
    if run_result.solved:
        quick_post_process_result = getattr(run_result, "quick_post_process_result", None)
        if quick_post_process_result is not None:
            post_processed_layout = quick_post_process_result["rooms"]
            wall_union_result = quick_post_process_result["wall_union"]
        else:
            post_processed_layout = run_result.solution
            wall_union_result = {"walls": [], "room_walls": {}}

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
    }


def run_fpg_pipeline_internal(
    should_optuna_run: bool = False,
    optuna_trial_count: int = DEFAULT_OPTUNA_TRIALS,
    verbose: bool = True,
) -> dict[str, Any]:
    """Internal pipeline: load server-side data, validate, solve and format payload."""
    started_at = perf_counter()
    SystemLogger.info(
        sector=1,
        message="v2 internal layout pipeline started",
        filename="algorithm_manager_v2.py",
        data={
            "should_optuna_run": bool(should_optuna_run),
            "optuna_trial_count": int(optuna_trial_count),
            "verbose": bool(verbose),
        },
    )

    try:
        templates, size_constraints, relation_constraints = _load_server_side_data()
        if not templates:
            return _error_payload(
                status="NO_TEMPLATE",
                message="No room template available in database",
            )

        template = templates[0]
        relation_constraints, prune_error = prune_room_relations_constraints_by_template(
            room_template=template,
            room_relations_constraints=relation_constraints,
        )
        if prune_error:
            return _error_payload(prune_error)

        is_valid, validation_message = pre_validation(
            room_template=template,
            room_size_constraints=size_constraints,
            floor_width=FLOOR_WIDTH,
            floor_height=FLOOR_HEIGHT,
        )
        if not is_valid:
            return _error_payload(validation_message or "Pre validation failed.")

        requirements = _build_requirements(
            floor_width=FLOOR_WIDTH,
            floor_height=FLOOR_HEIGHT,
            room_template=template,
            room_size_constraints=size_constraints,
            room_relations_constraints=relation_constraints,
        )
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
        payload = _build_payload_from_solver_result(run_result)
        SystemLogger.info(
            sector=1,
            message="v2 internal layout pipeline completed",
            filename="algorithm_manager_v2.py",
            data={
                "status": payload.get("status", "UNKNOWN"),
                "solved": bool(run_result.solved),
                "duration_ms": round((perf_counter() - started_at) * 1000.0, 2),
            },
        )
        return payload
    except Exception as exc:
        SystemLogger.error(
            sector=1,
            message="v2 internal layout pipeline failed",
            filename="algorithm_manager_v2.py",
            data={
                "error": str(exc),
                "duration_ms": round((perf_counter() - started_at) * 1000.0, 2),
            },
        )
        return _error_payload(f"Failed to generate layout: {exc}")


def run_fpg_pipeline_api(
    floor_width: float,
    floor_height: float,
    room_template: RoomSetupTemplateBase,
    should_optuna_run: bool = False,
    optuna_trial_count: int = DEFAULT_OPTUNA_TRIALS,
    verbose: bool = False,
) -> dict[str, Any]:
    """API pipeline: use caller dimensions/template, fetch constraints server-side, then solve."""
    started_at = perf_counter()
    SystemLogger.info(
        sector=1,
        message="v2 api layout pipeline started",
        filename="algorithm_manager_v2.py",
        data={
            "floor_width": float(floor_width),
            "floor_height": float(floor_height),
            "should_optuna_run": bool(should_optuna_run),
            "optuna_trial_count": int(optuna_trial_count),
            "verbose": bool(verbose),
        },
    )

    # WARNING: Its highly important to change `should_bypass` value to False when deploying
    try:
        _, size_constraints, relation_constraints = _load_server_side_data()
        print(f"\n\nBefore Prune: {relation_constraints}")
        relation_constraints, prune_error = prune_room_relations_constraints_by_template(
            room_template=room_template,
            room_relations_constraints=relation_constraints,
        )
        print(f"\nAfter Prune: {relation_constraints}\n\n")
        if prune_error:
            return _error_payload(prune_error)

        is_valid, validation_message = pre_validation(
            room_template=room_template,
            room_size_constraints=size_constraints,
            floor_width=floor_width,
            floor_height=floor_height,
        )
        if not is_valid:
            return _error_payload(validation_message or "Pre validation failed.")

        requirements = _build_requirements(
            floor_width=floor_width,
            floor_height=floor_height,
            room_template=room_template,
            room_size_constraints=size_constraints,
            room_relations_constraints=relation_constraints,
        )
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
        payload = _build_payload_from_solver_result(run_result)
        SystemLogger.info(
            sector=1,
            message="v2 api layout pipeline completed",
            filename="algorithm_manager_v2.py",
            data={
                "status": payload.get("status", "UNKNOWN"),
                "solved": bool(run_result.solved),
                "duration_ms": round((perf_counter() - started_at) * 1000.0, 2),
            },
        )
        return payload
    except Exception as exc:
        SystemLogger.error(
            sector=1,
            message="v2 api layout pipeline failed",
            filename="algorithm_manager_v2.py",
            data={
                "error": str(exc),
                "duration_ms": round((perf_counter() - started_at) * 1000.0, 2),
            },
        )
        return _error_payload(f"Failed to generate layout: {exc}")

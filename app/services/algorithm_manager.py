import contextlib
import io
from datetime import datetime
from time import perf_counter
from typing import Any, List

from app.algorithms.floor_plan_generator import FloorPlanGenerator
from app.algorithms.floor_plan_generator.types.room import (
    RoomData,
    ConfigData,
    FpgRequirements,
)
from app.core.config_fpg import (
    FLOOR_WIDTH,
    FLOOR_HEIGHT,
    MIN_COVERAGE,
    DEFAULT_OPTUNA_TRIALS,
    DEFAULT_OPTUNA_STORAGE_ENABLED,
    DEFAULT_OPTUNA_STORAGE_URL,
    DEFAULT_ASPECT_RATIO_MAX,
    DEFAULT_ASPECT_RATIO_MIN,
    DEFAULT_HALLWAY_COUNT,
    DEFAULT_MIN_W,
    DEFAULT_MIN_H,
    DEFAULT_MAX_W,
    DEFAULT_MAX_H,
    ENVELOPE_ENABLED,
    ENVELOPE_MIN_GAP,
    ENVELOPE_MAX_GAP,
    ENVELOPE_EXCLUDE_TYPES,
    ENVELOPE_APPLY_SIDES,
)
from app.algorithms.floor_plan_generator.fpg_score import score_layout
from app.algorithms.floor_plan_generator.fpg_optuna import (
    FpgEvaluationResult,
    OptunaOptimizationResult,
    run_optuna_optimization,
)
from app.algorithms.floor_plan_generator.fpg_post_process import (
    build_post_processed_layout,
)

from sqlmodel import Session
from app.core.database import engine
from app.crud import (
    room_size_constraint as room_size_constraint_crud,
    room_setup_template as room_setup_template_crud,
    room_relations_constraint as room_relations_constraint_crud,
)
from app.util.room_requirements import normalize_db_data_requirements
from app.util.dev_use_mock_db import (
    load_room_relations_constraints,
    load_room_setup_templates,
    load_room_size_constraints,
)
from app.util.logger import SystemLogger


# Fallback room dimension used when a room_size_constraints column is NULL.
# (unified in config_fpg)

EMPTY_POST_PROCESS_LAYOUT = {"walls": [], "rooms": []}




def _build_requirements_from_database() -> FpgRequirements | None:
    should_bypass = True

    if should_bypass:
        print("bypass function call")
        templates = load_room_setup_templates()
        size_constraints = load_room_size_constraints()
        relation_constraints = load_room_relations_constraints()
    else:
        with Session(engine) as session:
            templates = room_setup_template_crud.get_all(session)
            size_constraints = room_size_constraint_crud.get_all(session)
            relation_constraints = room_relations_constraint_crud.get_all(session)

    print(f"Retrieved {len(templates)} templates")
    print(f"Retrieved {len(size_constraints)} size constraints")
    print(f"Retrieved {len(relation_constraints)} relation constraints")

    # debug: print loaded values
    print("Templates:", templates)
    print("Size constraints:", size_constraints)
    print("Relation constraints:", relation_constraints)
    

    # If no templates, exit early
    if not templates:
        print("No room setup templates found in database")
        return None

    # Use the first template as the basis
    template = templates[0]
    print(f"\nUsing template: {template.name}")

    # Build RoomData list from template data
    rooms: List[RoomData] = []
    if template.data:
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

    print(f"Created {len(rooms)} RoomData objects")
    for room in rooms:
        print(f"  - {room.name} ({room.type}): {room.min_w}-{room.max_w} * {room.min_h}-{room.max_h}")

    # Normalize rooms based on database constraint rules
    print("\nNormalizing rooms against database constraints...")
    rooms = normalize_db_data_requirements(rooms, size_constraints)

    print(f"Normalized {len(rooms)} RoomData objects")
    for room in rooms:
        print(f"  - {room.name} ({room.type}): Min W: {room.min_w} - Max W: {room.max_w} * Min H: {room.min_h} - Max H: {room.max_h}")

    # Create ConfigData
        config = ConfigData(
            min_coverage=MIN_COVERAGE,
            max_aspect_ratio=DEFAULT_ASPECT_RATIO_MAX,
            min_aspect_ratio=DEFAULT_ASPECT_RATIO_MIN,
            floor_plan_width=FLOOR_WIDTH,
            floor_plan_height=FLOOR_HEIGHT,
            hallway_count=DEFAULT_HALLWAY_COUNT,
            envelope_enabled=ENVELOPE_ENABLED,
            envelope_min_gap=ENVELOPE_MIN_GAP,
            envelope_max_gap=ENVELOPE_MAX_GAP,
            envelope_exclude_types=ENVELOPE_EXCLUDE_TYPES,
            envelope_apply_sides=ENVELOPE_APPLY_SIDES,
        )
        
        # Create FpgRequirements with relation constraints
        print(f"Floor dimensions: {config.floor_plan_width} x {config.floor_plan_height}")
        requirements = FpgRequirements(
            rooms=rooms,
            config=config,
            relation_constraints=relation_constraints
        )
        return requirements

def _print_optuna_summary(result: OptunaOptimizationResult) -> None:
    print("\nOptuna Summary:")
    print(f"  - Study Name: {result.study_name}")
    print(f"  - Completed Trials: {result.completed_trials}")
    print(f"  - Failed/Zero Trials: {result.failed_trials}")
    print(f"  - Best Trial Number: {result.best_trial_number}")
    print(f"  - Best Score: {result.best_value}")
    print(f"  - Best Params: {result.best_params}")

    if result.best_run is not None:
        print("  - Best Run Status:")
        print(f"    * Solved: {result.best_run.solved}")
        print(f"    * Status: {result.best_run.status}")
        if result.best_run.score_report is not None:
            print(f"    * Valid: {result.best_run.score_report.valid}")
            print(f"    * Total Score: {result.best_run.score_report.total_score}")
        if result.best_run.solution:
            print("  - Best Layout (Coordinates):")
            for room_result in result.best_run.solution:
                print(
                    "    * "
                    f"{room_result['name']} ({room_result['type']}): "
                    f"x={room_result['x']}, y={room_result['y']}, "
                    f"w={room_result['w']}, h={room_result['h']}, "
                    f"area={room_result['area']}"
                )

def _RunFPG(requirements: FpgRequirements, verbose: bool = True) -> FpgEvaluationResult:
    if verbose:
        print(f"\nCreated FpgRequirements with {len(requirements.rooms)} rooms")
        print(f"\nRequirements {requirements}\n\n")
    
    # Initialize FloorPlanGenerator
    generator = FloorPlanGenerator(requirements)
    if verbose:
        print("FloorPlanGenerator initialized")
    
    # Generate floor plan
    if verbose:
        print("\nCalling generate()...")

    if verbose:
        solved = generator.generate()
    else:
        with contextlib.redirect_stdout(io.StringIO()):
            solved = generator.generate()

    status = generator.last_status_name
    
    if solved:
        if verbose:
            print("✓ Floor plan generated successfully!")
        solution = generator.get_solution()
        score_report = score_layout(solution, requirements)

        if verbose:
            print(f"\nSolution with {len(solution)} rooms:")
            for room_result in solution:
                print(f"  - {room_result['name']} ({room_result['type']})")
                print(f"    Position: ({room_result['x']}, {room_result['y']})")
                print(f"    Size: {room_result['w']} x {room_result['h']}")
                print(f"    Area: {room_result['area']}")

            print("\nScore Report:")
            print(f"  - Valid: {score_report.valid}")
            print(f"  - Total Score: {score_report.total_score}")
            print(f"  - Component Scores: {score_report.component_scores}")
            if score_report.hard_violations:
                print("  - Hard Violations:")
                for violation in score_report.hard_violations:
                    print(f"    * {violation}")
            print(f"  - Diagnostics: {score_report.diagnostics}")

            print("\nRaw Solution:")
            print(solution)

        return FpgEvaluationResult(
            solved=True,
            solution=solution,
            score_report=score_report,
            status=status,
            message="Solver found a layout",
        )
    else:
        if verbose:
            print(f"✗ Floor plan generation failed - no solution found ({status})")

        return FpgEvaluationResult(
            solved=False,
            solution=[],
            score_report=None,
            status=status,
            message="Solver did not return FEASIBLE/OPTIMAL",
        )
    
def _OptunaEntry(
    requirements: FpgRequirements,
    n_trials: int = 50,
    study_name: str = "fpg_layout_optimization",
) -> OptunaOptimizationResult:
    storage = DEFAULT_OPTUNA_STORAGE_URL if DEFAULT_OPTUNA_STORAGE_ENABLED else None
    mode = "database" if storage is not None else "in-memory"
    # Use a unique study name per run to avoid reusing old trials from previous executions.
    run_study_name = f"{study_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(
        f"\nRunning Optuna optimization for {n_trials} trials "
        f"({mode} study storage), study={run_study_name}..."
    )
    result = run_optuna_optimization(
        base_requirements=requirements,
        evaluator=_RunFPG,
        n_trials=n_trials,
        study_name=run_study_name,
        storage=storage,
    )

    _print_optuna_summary(result)
    return result

def _select_solver_result(
    requirements: FpgRequirements,
    use_optuna: bool,
    n_trials: int,
    verbose: bool,
) -> FpgEvaluationResult:
    """Return a single solver result selected from one-shot or Optuna flow."""
    SystemLogger.info(
        sector=1,
        message="solver selection",
        filename="algorithm_manager.py",
        data={"use_optuna": bool(use_optuna), "n_trials": int(n_trials)},
    )

    if not use_optuna:
        return _RunFPG(requirements, verbose=verbose)

    optuna_result = _OptunaEntry(requirements, n_trials=n_trials)
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
    """Transform solver output into API payload with post-processed geometry."""
    if run_result.solved:
        post_process = build_post_processed_layout(run_result.solution)
    else:
        post_process = EMPTY_POST_PROCESS_LAYOUT

    return {
        "status": run_result.status,
        "message": run_result.message,
        "walls": post_process["walls"],
        "rooms": post_process["rooms"],
    }

def run_layout_pipeline(
    use_optuna: bool = False,
    n_trials: int = DEFAULT_OPTUNA_TRIALS,
    verbose: bool = False,
) -> dict[str, Any]:
    """Main orchestrator: DB requirements -> solve -> post-process -> payload."""
    started_at = perf_counter()
    SystemLogger.info(
        sector=1,
        message="layout pipeline started",
        filename="algorithm_manager.py",
        data={
            "use_optuna": bool(use_optuna),
            "n_trials": int(n_trials),
            "verbose": bool(verbose),
        },
    )

    try:
        requirements = _build_requirements_from_database()
        if requirements is None:
            SystemLogger.warning(
                sector=1,
                message="layout pipeline ended without template",
                filename="algorithm_manager.py",
                data={"status": "NO_TEMPLATE"},
            )
            return {
                "status": "NO_TEMPLATE",
                "message": "No room template available in database",
                "walls": [],
                "rooms": [],
            }

        run_result = _select_solver_result(
            requirements=requirements,
            use_optuna=use_optuna,
            n_trials=n_trials,
            verbose=verbose,
        )
        payload = _build_payload_from_solver_result(run_result)
        SystemLogger.info(
            sector=1,
            message="layout pipeline completed",
            filename="algorithm_manager.py",
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
            message="layout pipeline failed",
            filename="algorithm_manager.py",
            data={
                "error": str(exc),
                "duration_ms": round((perf_counter() - started_at) * 1000.0, 2),
            },
        )
        return {
            "status": "ERROR",
            "message": f"Failed to generate layout: {exc}",
            "walls": [],
            "rooms": [],
        }

def DEV_RUN() -> None:
    """Development entrypoint for the full solve -> post-process pipeline."""
    
    requirements = _build_requirements_from_database()
    _RunFPG (requirements=requirements , verbose=True)
        
        
            
            


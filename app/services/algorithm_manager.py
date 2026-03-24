import contextlib
import io
from typing import Any, List

from app.algorithms.floor_plan_generator import FloorPlanGenerator
from app.algorithms.floor_plan_generator.types.room import (
    RoomData,
    ConfigData,
    FpgRequirements,
)
from app.algorithms.floor_plan_generator.config import (
    FLOOR_WIDTH,
    FLOOR_HEIGHT,
    MIN_COVERAGE,
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
from app.util.room_requirements import normalize_requirements


# Fallback room dimension used when a room_size_constraints column is NULL.
DEFAULT_ROOM_DIMENSION = 1000


EMPTY_POST_PROCESS_LAYOUT = {"walls": [], "rooms": []}
DEFAULT_OPTUNA_TRIALS = 20




def _build_requirements_from_database() -> FpgRequirements | None:
    with Session(engine) as session:
        # Retrieve all database records
        templates = room_setup_template_crud.get_all(session)
        size_constraints = room_size_constraint_crud.get_all(session)
        relation_constraints = room_relations_constraint_crud.get_all(session)
        
        print(f"Retrieved {len(templates)} templates")
        print(f"Retrieved {len(size_constraints)} size constraints")
        print(f"Retrieved {len(relation_constraints)} relation constraints")
        
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
                        min_w=1,
                        min_h=1,
                        max_w=1,
                        max_h=1,
                    )
                )
        
        print(f"Created {len(rooms)} RoomData objects")
        for room in rooms:
            print(f"  - {room.name} ({room.type}): {room.min_w}-{room.max_w} * {room.min_h}-{room.max_h}")
        
        # Normalize rooms based on database constraint rules
        print("\nNormalizing rooms against database constraints...")
        rooms = normalize_requirements(rooms, size_constraints)
        
        print(f"Normalized {len(rooms)} RoomData objects")
        for room in rooms:
            print(f"  - {room.name} ({room.type}): Min W: {room.min_w} - Max W: {room.max_w} * Min H: {room.min_h} - Max H: {room.max_h}")
        
        # Create ConfigData
        config = ConfigData(
            min_coverage=MIN_COVERAGE,
            max_aspect_ratio=16.0,
            min_aspect_ratio=0.0,
            floor_plan_width=FLOOR_WIDTH,
            floor_plan_height=FLOOR_HEIGHT,
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
    storage: str | None = "sqlite:///optuna_fpg.db",
) -> OptunaOptimizationResult:
    print(f"\nRunning Optuna optimization for {n_trials} trials...")
    result = run_optuna_optimization(
        base_requirements=requirements,
        evaluator=_RunFPG,
        n_trials=n_trials,
        study_name=study_name,
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
    try:
        requirements = _build_requirements_from_database()
        if requirements is None:
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
        return _build_payload_from_solver_result(run_result)
    except Exception as exc:
        return {
            "status": "ERROR",
            "message": f"Failed to generate layout: {exc}",
            "walls": [],
            "rooms": [],
        }

def DEV_RUN(use_optuna: bool = True, n_trials: int = 50) -> None:
    """Development entrypoint for the full solve -> post-process pipeline."""
    payload = run_layout_pipeline(
        use_optuna=use_optuna,
        n_trials=n_trials,
        verbose=True,
    )
    print("\nPost-Process Summary:")
    print(f"  - Status: {payload['status']}")
    print(f"  - Message: {payload['message']}")
    print(f"  - Walls: {len(payload['walls'])}")
    print(f"  - Rooms: {len(payload['rooms'])}")
        
        
            
            


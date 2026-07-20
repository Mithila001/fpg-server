# app/pipeline/generation/pipeline.py
from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Any, TypeVar

from app.algorithms.candidate_scoring import (
    CandidateScoringInput,
    evaluate_candidate,
)
from app.algorithms.candidate_scoring import (
    create_default_config as create_candidate_scoring_config,
)
from app.algorithms.candidate_scoring import (
    create_default_registry as create_candidate_scoring_registry,
)
from app.algorithms.candidate_search import (
    CandidateSearchInput,
    CandidateSearchSettings,
    CandidateSearchTarget,
    search_candidates,
)
from app.algorithms.floor_plan_openings import (
    OpeningGenerationError,
    OpeningGenerationRequest,
    generate_openings,
)
from app.algorithms.floor_plan_post_processing import (
    INITIAL_GENERATION_PROFILE as POST_PROCESSING_PROFILE,
)
from app.algorithms.floor_plan_post_processing import (
    PipelineStatus,
    PostProcessingRequest,
    post_process_floor_plan,
)
from app.algorithms.floor_plan_preprocessing import (
    FloorLimits,
    FloorPlanPreprocessingError,
    PreprocessingInput,
    PreprocessingRequest,
    RequestedRoom,
    prepare_generation_input,
)
from app.algorithms.floor_plan_scoring import (
    FloorPlanScoringError,
    score_floor_plan,
)
from app.algorithms.floor_plan_solver import (
    INITIAL_GENERATION_PROFILE as SOLVER_PROFILE,
)
from app.algorithms.floor_plan_solver import (
    FloorPlanSolveRequest,
    FloorPlanSolverError,
    RoomPlacementHint,
    generate_floor_plan,
)

from .context import (
    GenerationPipelineError,
    GenerationPipelineRequest,
    GenerationPipelineResult,
    GenerationPipelineSettings,
    GenerationStage,
    load_generation_reference_data,
)

T = TypeVar("T")


def _error_code(exc: Exception) -> str:
    name = type(exc).__name__
    return "".join(
        ("_" + character.lower()) if character.isupper() else character
        for character in name
    ).lstrip("_")


def _run_stage(
    request_id: str,
    stage: GenerationStage,
    operation: Callable[[], T],
    *,
    expected_errors: tuple[type[Exception], ...] = (),
    summary: Callable[[T], str] | None = None,
) -> T:
    started = perf_counter()
    print(f"[generation:{request_id}] {stage.value} started")
    try:
        result = operation()
    except GenerationPipelineError as exc:
        duration_ms = (perf_counter() - started) * 1000
        print(
            f"[generation:{request_id}] {stage.value} failed "
            f"code={exc.code} duration_ms={duration_ms:.1f}: {exc.message}"
        )
        raise
    except expected_errors as exc:
        duration_ms = (perf_counter() - started) * 1000
        error = GenerationPipelineError(stage, _error_code(exc), str(exc))
        print(
            f"[generation:{request_id}] {stage.value} failed "
            f"code={error.code} duration_ms={duration_ms:.1f}: {error.message}"
        )
        raise error from exc
    except Exception as exc:
        duration_ms = (perf_counter() - started) * 1000
        print(
            f"[generation:{request_id}] {stage.value} failed "
            f"code=unexpected_error duration_ms={duration_ms:.1f}: {exc}"
        )
        raise

    duration_ms = (perf_counter() - started) * 1000
    suffix = f" {summary(result)}" if summary is not None else ""
    print(
        f"[generation:{request_id}] {stage.value} completed "
        f"duration_ms={duration_ms:.1f}{suffix}"
    )
    return result


def run_generation_pipeline(
    request: GenerationPipelineRequest,
    *,
    settings: GenerationPipelineSettings = GenerationPipelineSettings(),
) -> GenerationPipelineResult:
    """Run the cleaned floor-plan features as one orchestration-only pipeline."""

    def preprocess():
        preprocessing_input = PreprocessingInput(
            request=PreprocessingRequest(
                floor_limits=FloorLimits(request.max_width, request.max_height),
                aspect_ratio=request.aspect_ratio,
                rooms=tuple(
                    RequestedRoom(
                        room_type=room.room_type,
                        id=room.id,
                        name=room.name,
                        requested_size=room.requested_size,
                        required=room.required,
                    )
                    for room in request.rooms
                ),
            ),
            reference_data=load_generation_reference_data(),
        )
        return prepare_generation_input(preprocessing_input)

    prepared = _run_stage(
        request.request_id,
        GenerationStage.PREPROCESSING,
        preprocess,
        expected_errors=(FloorPlanPreprocessingError,),
        summary=lambda value: f"rooms={len(value.generation_spec.rooms)}",
    )
    specification = prepared.generation_spec

    candidate_registry = create_candidate_scoring_registry()
    candidate_config = create_candidate_scoring_config()

    def score_candidate(points: tuple[Any, ...]) -> float:
        result = evaluate_candidate(
            CandidateScoringInput(
                specification=specification,
                candidate=points,
            ),
            registry=candidate_registry,
            config=candidate_config,
        )
        return result.total_score

    search_result = _run_stage(
        request.request_id,
        GenerationStage.CANDIDATE_SEARCH,
        lambda: search_candidates(
            CandidateSearchInput(
                targets=tuple(
                    CandidateSearchTarget(room.id) for room in specification.rooms
                ),
                settings=CandidateSearchSettings(
                    min_x=0.0,
                    max_x=specification.floor.width,
                    min_y=0.0,
                    max_y=specification.floor.height,
                    grid_resolution=settings.candidate_grid_resolution,
                    trial_count=settings.candidate_trial_count,
                    random_seed=settings.candidate_random_seed,
                ),
                evaluator=score_candidate,
            )
        ),
        expected_errors=(TypeError, ValueError, RuntimeError),
        summary=lambda value: (
            f"score={value.score:.2f} trials={value.completed_trials}"
        ),
    )

    def solve():
        result = generate_floor_plan(
            FloorPlanSolveRequest(
                specification=specification,
                profile=SOLVER_PROFILE,
                candidate_hints=tuple(
                    RoomPlacementHint(point.room_id, point.x, point.y)
                    for point in search_result.points
                ),
            )
        )
        if not result.solved:
            raise GenerationPipelineError(
                GenerationStage.SOLVER,
                f"solver_{result.status.value}",
                result.message,
                {"diagnostics": result.diagnostics},
            )
        return result

    solve_result = _run_stage(
        request.request_id,
        GenerationStage.SOLVER,
        solve,
        expected_errors=(FloorPlanSolverError,),
        summary=lambda value: f"status={value.status.value}",
    )
    solved_floor_plan = solve_result.floor_plan
    if solved_floor_plan is None:
        raise GenerationPipelineError(
            GenerationStage.SOLVER,
            "solver_missing_floor_plan",
            "Solver reported success without returning a floor plan.",
        )

    def post_process():
        result = post_process_floor_plan(
            PostProcessingRequest(
                floor_plan=solved_floor_plan,
                profile=POST_PROCESSING_PROFILE,
                specification=specification,
                request_id=request.request_id,
            )
        )
        if result.status is PipelineStatus.FAILED:
            failure = result.failure
            raise GenerationPipelineError(
                GenerationStage.POST_PROCESSING,
                failure.code if failure else "post_processing_failed",
                failure.message if failure else "Floor-plan post-processing failed.",
                {"executions": result.executions},
            )
        return result

    post_result = _run_stage(
        request.request_id,
        GenerationStage.POST_PROCESSING,
        post_process,
        summary=lambda value: f"rooms={len(value.floor_plan.rooms)}",
    )

    def add_openings():
        result = generate_openings(
            OpeningGenerationRequest(
                floor_plan=post_result.floor_plan,
                request_id=request.request_id,
            )
        )
        if not result.solved:
            raise GenerationPipelineError(
                GenerationStage.OPENINGS,
                f"openings_{result.status.value}",
                result.message,
                {"diagnostics": result.diagnostics},
            )
        return result

    opening_result = _run_stage(
        request.request_id,
        GenerationStage.OPENINGS,
        add_openings,
        expected_errors=(OpeningGenerationError,),
        summary=lambda value: (
            f"openings={len(value.floor_plan.openings)}"
            if value.floor_plan is not None
            else "openings=0"
        ),
    )
    opened_floor_plan = opening_result.floor_plan
    if opened_floor_plan is None:
        raise GenerationPipelineError(
            GenerationStage.OPENINGS,
            "openings_missing_floor_plan",
            "Opening generation reported success without returning a floor plan.",
        )

    scoring_result = _run_stage(
        request.request_id,
        GenerationStage.SCORING,
        lambda: score_floor_plan(opened_floor_plan, specification),
        expected_errors=(FloorPlanScoringError,),
        summary=lambda value: (
            f"score={value.total_score:.2f} passed_critical={value.passed_critical}"
        ),
    )
    return GenerationPipelineResult(
        floor_plan=opened_floor_plan,
        scoring=scoring_result,
    )

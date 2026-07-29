# app/pipeline/generation/pipeline.py
from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from inspect import signature
from math import ceil, sqrt
from time import perf_counter
from typing import Any, Protocol, TypeVar, cast

import app.algorithms.floor_plan_solver as floor_plan_solver_module
from app.algorithms.candidate_scoring import (
    CandidateScoringInput,
    evaluate_candidate,
)
from app.algorithms.candidate_scoring import (
    ScoringResult as CandidateScoringResult,
)
from app.algorithms.candidate_scoring import (
    create_default_config as create_candidate_scoring_config,
)
from app.algorithms.candidate_scoring import (
    create_default_registry as create_candidate_scoring_registry,
)
from app.algorithms.candidate_search import (
    CandidateSearchInput,
    CandidateSearchSession,
    CandidateSearchSettings,
    CandidateSearchTarget,
    CandidateTrialResult,
)
from app.algorithms.floor_plan_openings import (
    OpeningGenerationError,
    OpeningGenerationRequest,
    OpeningGenerationResult,
    generate_openings,
)
from app.algorithms.floor_plan_post_processing import (
    INITIAL_GENERATION_PROFILE as POST_PROCESSING_PROFILE,
)
from app.algorithms.floor_plan_post_processing import (
    PipelineStatus,
    PostProcessingRequest,
    PostProcessingResult,
    post_process_floor_plan,
)
from app.algorithms.floor_plan_preprocessing import (
    FloorLimits,
    FloorPlanPreprocessingError,
    PreparedGenerationInput,
    PreprocessingInput,
    PreprocessingRequest,
    RequestedRoom,
    prepare_generation_input,
)
from app.algorithms.floor_plan_scoring import (
    FloorPlanScoringError,
    FloorPlanScoringResult,
    score_floor_plan,
)
from app.algorithms.floor_plan_scoring.logging import (
    log_floor_plan_scoring_result,
)
from app.algorithms.floor_plan_solver import (
    INITIAL_GENERATION_PROFILE,
    FloorPlanSolveRequest,
    FloorPlanSolveResult,
    FloorPlanSolverError,
    RoomPlacementHint,
    generate_floor_plan,
)
from app.algorithms.types_new import FloorPlan
from app.core.execution import ExecutionContext, PipelineStage
from app.streaming.cancellation import GenerationCancellationSignal
from app.streaming.contracts import (
    CompletionOutcome,
    FloorPlanClassification,
    GenerationEventPublisher,
    GenerationStatus,
    NullGenerationEventPublisher,
)
from app.visualization.api import (
    CandidatePoint as VisualizationCandidatePoint,
)
from app.visualization.api import (
    CandidateSearchVisualization,
    FloorPlanFlowVisualization,
    FloorPlanVisualizationStage,
    SearchBounds,
    render_candidate_scoring_features,
    render_candidate_search,
    render_floor_plan_general,
    render_floor_plan_scoring_features,
)

from .context import (
    GenerationPipelineError,
    GenerationPipelineRequest,
    GenerationPipelineResult,
    GenerationPipelineSettings,
    GenerationStage,
    load_generation_reference_data,
)
from .logging import (
    create_pipeline_context,
    log_pipeline_event,
    save_final_floor_plan,
)

T = TypeVar("T")

_REFINEMENT_PROFILE_EXPORTS: tuple[tuple[str, ...], ...] = (
    ("REFINEMENT_A_PROFILE", "REFINEMENT_PROFILE_A"),
    ("REFINEMENT_B_PROFILE", "REFINEMENT_PROFILE_B"),
)
_REFINEMENT_FLOOR_PLAN_ARGUMENTS = (
    "existing_floor_plan",
    "floor_plan",
    "source_floor_plan",
    "input_floor_plan",
    "base_floor_plan",
)


@dataclass(slots=True)
class _CompletedFloorPlanAttempt:
    search_trial_id: int | None
    candidate_id: int
    candidate_score: float
    solver_run_id: int
    initial_floor_plan: FloorPlan
    refined_floor_plan: FloorPlan
    post_processed_floor_plan: FloorPlan
    final_floor_plan: FloorPlan
    scoring: FloorPlanScoringResult


class _SolverAttemptVisualization(Protocol):
    solver_run_id: int
    initial_floor_plan: FloorPlan
    refined_floor_plan: FloorPlan
    final_floor_plan: FloorPlan


def _log_generation(
    context: ExecutionContext,
    event: str,
    level: str = "INFO",
    data: dict[str, object] | None = None,
) -> None:
    log_pipeline_event(
        context,
        event,
        level=level,
        payload=data,
    )


def _error_code(exc: Exception) -> str:
    name = type(exc).__name__
    return "".join(
        ("_" + character.lower()) if character.isupper() else character
        for character in name
    ).lstrip("_")


def _run_stage(
    context: ExecutionContext,
    stage: GenerationStage,
    operation: Callable[[], T],
    *,
    expected_errors: tuple[type[Exception], ...] = (),
    summary: Callable[[T], str] | None = None,
    label: str | None = None,
) -> T:
    started = perf_counter()
    stage_label = label or stage.value
    stage_context = context.with_stage(_execution_stage(stage))
    _log_generation(
        stage_context,
        "stage_started",
        data={"stage": stage.value, "label": stage_label},
    )

    try:
        result = operation()
    except GenerationPipelineError as exc:
        duration_ms = (perf_counter() - started) * 1000
        _log_generation(
            stage_context,
            "stage_failed",
            "ERROR",
            {
                "stage": stage.value,
                "label": stage_label,
                "code": exc.code,
                "duration_ms": duration_ms,
                "message": exc.message,
            },
        )
        raise
    except expected_errors as exc:
        duration_ms = (perf_counter() - started) * 1000
        error = GenerationPipelineError(stage, _error_code(exc), str(exc))
        _log_generation(
            stage_context,
            "stage_failed",
            "ERROR",
            {
                "stage": stage.value,
                "label": stage_label,
                "code": error.code,
                "duration_ms": duration_ms,
                "message": error.message,
            },
        )
        raise error from exc
    except Exception as exc:
        duration_ms = (perf_counter() - started) * 1000
        _log_generation(
            stage_context,
            "stage_failed",
            "ERROR",
            {
                "stage": stage.value,
                "label": stage_label,
                "code": "unexpected_error",
                "duration_ms": duration_ms,
                "error_type": type(exc).__name__,
                "message": str(exc),
            },
        )
        raise

    duration_ms = (perf_counter() - started) * 1000
    _log_generation(
        stage_context,
        "stage_completed",
        data={
            "stage": stage.value,
            "label": stage_label,
            "duration_ms": duration_ms,
            "summary": summary(result) if summary is not None else None,
        },
    )
    return result


def _execution_stage(stage: GenerationStage) -> PipelineStage:
    aliases = {
        GenerationStage.ATTEMPT_SCORING: PipelineStage.FLOOR_PLAN_SCORING,
        GenerationStage.SCORING: PipelineStage.FLOOR_PLAN_SCORING,
        GenerationStage.FINAL_VALIDATION: PipelineStage.FINALIZATION,
    }
    if stage in aliases:
        return aliases[stage]
    return PipelineStage(stage.value)


def _load_refinement_profiles() -> tuple[Any, ...]:
    profiles: list[Any] = []
    missing_exports: list[str] = []

    for aliases in _REFINEMENT_PROFILE_EXPORTS:
        profile = next(
            (
                getattr(floor_plan_solver_module, export_name)
                for export_name in aliases
                if hasattr(floor_plan_solver_module, export_name)
            ),
            None,
        )
        if profile is None:
            missing_exports.append("/".join(aliases))
        else:
            profiles.append(profile)

    if missing_exports:
        raise GenerationPipelineError(
            GenerationStage.REFINEMENT,
            "missing_refinement_profiles",
            "The floor-plan solver does not export all required refinement profiles.",
            {"missing_exports": tuple(missing_exports)},
        )

    return tuple(profiles)


def _profile_name(profile: Any) -> str:
    for attribute_name in ("name", "profile_name", "id"):
        value = getattr(profile, attribute_name, None)
        if value is not None:
            return str(value)
    return type(profile).__name__


def _create_solver_request(
    *,
    specification: Any,
    profile: Any,
    candidate_hints: tuple[RoomPlacementHint, ...],
    floor_plan: FloorPlan | None = None,
    context: ExecutionContext | None = None,
) -> FloorPlanSolveRequest:
    request_arguments: dict[str, Any] = {
        "specification": specification,
        "profile": profile,
        "candidate_hints": candidate_hints,
        "execution_context": context,
    }

    if floor_plan is not None:
        available_parameters = signature(FloorPlanSolveRequest).parameters
        floor_plan_argument = next(
            (
                argument_name
                for argument_name in _REFINEMENT_FLOOR_PLAN_ARGUMENTS
                if argument_name in available_parameters
            ),
            None,
        )
        if floor_plan_argument is None:
            raise GenerationPipelineError(
                GenerationStage.REFINEMENT,
                "unsupported_refinement_request",
                "FloorPlanSolveRequest has no supported input floor-plan field.",
                {"parameters": tuple(available_parameters)},
            )
        request_arguments[floor_plan_argument] = floor_plan

    return FloorPlanSolveRequest(**request_arguments)


def _default_candidate_hints(specification: Any) -> tuple[RoomPlacementHint, ...]:
    room_count = len(specification.rooms)
    if room_count == 0:
        return ()

    columns = max(1, ceil(sqrt(room_count)))
    rows = max(1, ceil(room_count / columns))
    horizontal_step = specification.floor.width / (columns + 1)
    vertical_step = specification.floor.length / (rows + 1)

    return tuple(
        RoomPlacementHint(
            room.id,
            (index % columns + 1) * horizontal_step,
            (index // columns + 1) * vertical_step,
        )
        for index, room in enumerate(specification.rooms)
    )


def _candidate_hints(
    trial: CandidateTrialResult,
) -> tuple[RoomPlacementHint, ...]:
    return tuple(
        RoomPlacementHint(point.room_id, point.x, point.y) for point in trial.points
    )


def _elapsed_seconds(started: float) -> float:
    return perf_counter() - started


def _timed_out(started: float, settings: GenerationPipelineSettings) -> bool:
    return _elapsed_seconds(started) >= settings.timeout_seconds


def _raise_if_cancelled(
    *,
    cancellation: GenerationCancellationSignal | None,
    context: ExecutionContext,
    started: float,
) -> None:
    if cancellation is None or not cancellation.is_cancelled:
        return

    reason = cancellation.reason or "cancellation_requested"
    elapsed_seconds = _elapsed_seconds(started)
    _log_generation(
        context,
        "flow_cancelled",
        data={
            "reason": reason,
            "elapsed_seconds": elapsed_seconds,
        },
    )
    raise GenerationPipelineError(
        GenerationStage.CANCELLATION,
        "generation_cancelled",
        "Generation was cancelled before completion.",
        {
            "termination_reason": "cancelled",
            "reason": reason,
            "elapsed_seconds": elapsed_seconds,
        },
    )


def _passes_critical_requirement(
    scoring: FloorPlanScoringResult,
    settings: GenerationPipelineSettings,
) -> bool:
    return not settings.require_final_critical_pass or scoring.passed_critical


def _is_usable(
    attempt: _CompletedFloorPlanAttempt,
    settings: GenerationPipelineSettings,
) -> bool:
    return (
        _passes_critical_requirement(attempt.scoring, settings)
        and attempt.scoring.total_score >= settings.usable_floor_plan_score
    )


def _is_presentable(
    attempt: _CompletedFloorPlanAttempt,
    settings: GenerationPipelineSettings,
) -> bool:
    return (
        _passes_critical_requirement(attempt.scoring, settings)
        and attempt.scoring.total_score
        >= settings.effective_presentable_floor_plan_score
    )


def _is_better_attempt(
    candidate: _CompletedFloorPlanAttempt,
    current_best: _CompletedFloorPlanAttempt | None,
) -> bool:
    if current_best is None:
        return True

    candidate_key = (
        candidate.scoring.passed_critical,
        candidate.scoring.total_score,
    )
    current_key = (
        current_best.scoring.passed_critical,
        current_best.scoring.total_score,
    )
    return candidate_key > current_key


def _render_candidate_trial(
    *,
    context: ExecutionContext,
    trial: CandidateTrialResult,
    settings: CandidateSearchSettings,
) -> None:
    payload = CandidateSearchVisualization(
        trial_number=trial.trial_number,
        score=trial.score,
        points=tuple(
            VisualizationCandidatePoint(
                room_id=str(point.room_id),
                x=int(point.x),
                y=int(point.y),
            )
            for point in trial.points
        ),
        bounds=SearchBounds(
            min_x=int(settings.min_x),
            max_x=int(settings.max_x),
            min_y=int(settings.min_y),
            max_y=int(settings.max_y),
        ),
        grid_resolution=max(1, int(settings.grid_resolution)),
        trial_count=settings.trial_count,
        metadata={
            "trial_number": trial.trial_number,
            "completed_trials": trial.completed_trials,
            "result": "eligible_candidate",
        },
    )
    render_candidate_search(
        payload,
        output_name=f"eligible-candidate-{trial.trial_number}",
        context=context.with_stage(PipelineStage.VISUALIZATION),
    )


def _render_candidate_scoring(
    *,
    context: ExecutionContext,
    scoring_input: CandidateScoringInput,
    scoring_result: CandidateScoringResult,
    settings: GenerationPipelineSettings,
) -> None:
    render_candidate_scoring_features(
        scoring_input,
        scoring_result,
        visualization_config=settings.scoring_visualization,
        context=context.with_stage(PipelineStage.VISUALIZATION),
    )


def _render_floor_plan_scoring(
    *,
    context: ExecutionContext,
    floor_plan: FloorPlan,
    scoring_result: FloorPlanScoringResult,
    settings: GenerationPipelineSettings,
) -> None:
    render_floor_plan_scoring_features(
        floor_plan,
        scoring_result,
        visualization_config=settings.scoring_visualization,
        context=context.with_stage(PipelineStage.VISUALIZATION),
    )


def _render_solver_attempt(
    *,
    context: ExecutionContext,
    attempt: _SolverAttemptVisualization,
    last_refinement_profile_name: str,
) -> None:
    stage_prefix = (
        f"candidate-{context.candidate_id}-run-{attempt.solver_run_id}"
    )
    payload = FloorPlanFlowVisualization(
        stages=(
            FloorPlanVisualizationStage(
                stage_id=f"{stage_prefix}-initial",
                stage_name="Initial Generation",
                category="solver",
                profile_name=_profile_name(INITIAL_GENERATION_PROFILE),
                floor_plan=deepcopy(attempt.initial_floor_plan),
            ),
            FloorPlanVisualizationStage(
                stage_id=f"{stage_prefix}-last-refined",
                stage_name="Last Refined Generation",
                category="solver_refinement",
                profile_name=last_refinement_profile_name,
                floor_plan=deepcopy(attempt.refined_floor_plan),
            ),
            FloorPlanVisualizationStage(
                stage_id=f"{stage_prefix}-final",
                stage_name="Final Floor Plan",
                category="final",
                profile_name="final",
                floor_plan=deepcopy(attempt.final_floor_plan),
            ),
        )
    )
    render_floor_plan_general(
        payload,
        output_prefix=stage_prefix,
        context=context.with_stage(PipelineStage.VISUALIZATION),
    )


def _execute_solver_run(
    *,
    request: GenerationPipelineRequest,
    specification: Any,
    search_trial_id: int | None,
    candidate_id: int,
    candidate_score: float,
    candidate_hints: tuple[RoomPlacementHint, ...],
    solver_run_id: int,
    refinement_profiles: tuple[Any, ...],
    settings: GenerationPipelineSettings,
    context: ExecutionContext,
    check_cancellation: Callable[[], None],
) -> _CompletedFloorPlanAttempt:
    check_cancellation()
    attempt_label = f"candidate-{candidate_id}.solver-run-{solver_run_id}"

    def solve_initial() -> FloorPlanSolveResult:
        result = generate_floor_plan(
            _create_solver_request(
                specification=specification,
                profile=INITIAL_GENERATION_PROFILE,
                candidate_hints=candidate_hints,
                context=context.with_stage(PipelineStage.SOLVER),
            )
        )
        if not result.solved:
            raise GenerationPipelineError(
                GenerationStage.SOLVER,
                f"solver_{result.status.value}",
                result.message,
                {"diagnostics": result.diagnostics},
            )
        if result.floor_plan is None:
            raise GenerationPipelineError(
                GenerationStage.SOLVER,
                "solver_missing_floor_plan",
                "Solver reported success without returning a floor plan.",
            )
        return result

    initial_result = _run_stage(
        context,
        GenerationStage.SOLVER,
        solve_initial,
        expected_errors=(FloorPlanSolverError,),
        summary=lambda value: f"status={value.status.value}",
        label=f"{attempt_label}.initial_generation",
    )
    check_cancellation()
    current_floor_plan = cast(FloorPlan, initial_result.floor_plan)
    initial_floor_plan = deepcopy(current_floor_plan)

    for refinement_index, profile in enumerate(refinement_profiles, start=1):
        profile_name = _profile_name(profile)

        def refine(
            active_profile: Any = profile,
            source_floor_plan: FloorPlan = current_floor_plan,
        ) -> FloorPlanSolveResult:
            result = generate_floor_plan(
                _create_solver_request(
                    specification=specification,
                    profile=active_profile,
                    candidate_hints=candidate_hints,
                    floor_plan=source_floor_plan,
                    context=context.with_stage(PipelineStage.REFINEMENT),
                )
            )
            if not result.solved:
                raise GenerationPipelineError(
                    GenerationStage.REFINEMENT,
                    f"refinement_{result.status.value}",
                    result.message,
                    {
                        "profile": profile_name,
                        "diagnostics": result.diagnostics,
                    },
                )
            if result.floor_plan is None:
                raise GenerationPipelineError(
                    GenerationStage.REFINEMENT,
                    "refinement_missing_floor_plan",
                    "Refinement reported success without a floor plan.",
                    {"profile": profile_name},
                )
            return result

        refinement_result = _run_stage(
            context,
            GenerationStage.REFINEMENT,
            refine,
            expected_errors=(FloorPlanSolverError,),
            summary=lambda value: f"status={value.status.value}",
            label=(f"{attempt_label}.refinement-{refinement_index}[{profile_name}]"),
        )
        check_cancellation()
        current_floor_plan = cast(FloorPlan, refinement_result.floor_plan)

    refined_floor_plan = deepcopy(current_floor_plan)

    def post_process() -> PostProcessingResult:
        result = post_process_floor_plan(
            PostProcessingRequest(
                floor_plan=refined_floor_plan,
                profile=POST_PROCESSING_PROFILE,
                specification=specification,
                request_id=f"{request.request_id}-{attempt_label}",
                execution_context=context.with_stage(PipelineStage.POST_PROCESSING),
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
        context,
        GenerationStage.POST_PROCESSING,
        post_process,
        summary=lambda value: f"rooms={len(value.floor_plan.rooms)}",
        label=f"{attempt_label}.post_processing",
    )
    check_cancellation()
    post_processed_floor_plan = deepcopy(post_result.floor_plan)

    def add_openings() -> OpeningGenerationResult:
        result = generate_openings(
            OpeningGenerationRequest(
                floor_plan=post_processed_floor_plan,
                request_id=f"{request.request_id}-{attempt_label}",
                execution_context=context.with_stage(PipelineStage.OPENINGS),
            )
        )
        if not result.solved:
            raise GenerationPipelineError(
                GenerationStage.OPENINGS,
                f"openings_{result.status.value}",
                result.message,
                {"diagnostics": result.diagnostics},
            )
        if result.floor_plan is None:
            raise GenerationPipelineError(
                GenerationStage.OPENINGS,
                "openings_missing_floor_plan",
                "Opening generation reported success without returning a floor plan.",
            )
        return result

    opening_result = _run_stage(
        context,
        GenerationStage.OPENINGS,
        add_openings,
        expected_errors=(OpeningGenerationError,),
        summary=lambda value: (
            f"openings={len(value.floor_plan.openings)}"
            if value.floor_plan is not None
            else "openings=0"
        ),
        label=f"{attempt_label}.openings",
    )
    check_cancellation()
    final_floor_plan = cast(FloorPlan, opening_result.floor_plan)

    scoring = _run_stage(
        context,
        GenerationStage.ATTEMPT_SCORING,
        lambda: score_floor_plan(
            final_floor_plan,
            specification,
            execution_context=context.with_stage(PipelineStage.FLOOR_PLAN_SCORING),
        ),
        expected_errors=(FloorPlanScoringError,),
        summary=lambda value: (
            f"score={value.total_score:.2f} passed_critical={value.passed_critical}"
        ),
        label=f"{attempt_label}.floor_plan_scoring",
    )
    check_cancellation()
    log_floor_plan_scoring_result(
        scoring,
        context=context.with_stage(PipelineStage.FLOOR_PLAN_SCORING),
        request_id=request.request_id,
        candidate_id=candidate_id,
        search_trial_id=search_trial_id,
        candidate_score=candidate_score,
        solver_run_id=solver_run_id,
        usable_threshold=settings.usable_floor_plan_score,
        presentable_threshold=(settings.effective_presentable_floor_plan_score),
    )

    attempt = _CompletedFloorPlanAttempt(
        search_trial_id=search_trial_id,
        candidate_id=candidate_id,
        candidate_score=candidate_score,
        solver_run_id=solver_run_id,
        initial_floor_plan=initial_floor_plan,
        refined_floor_plan=refined_floor_plan,
        post_processed_floor_plan=post_processed_floor_plan,
        final_floor_plan=deepcopy(final_floor_plan),
        scoring=scoring,
    )

    if settings.scoring_visualization.enabled:
        try:
            _run_stage(
                context,
                GenerationStage.VISUALIZATION,
                lambda: _render_floor_plan_scoring(
                    context=context,
                    floor_plan=final_floor_plan,
                    scoring_result=scoring,
                    settings=settings,
                ),
                label=f"{attempt_label}.floor_plan_scoring_visualization",
            )
        except Exception as exc:
            _log_generation(
                context,
                "visualization_skipped",
                "WARNING",
                {
                    "search_trial_id": search_trial_id,
                    "solver_run_id": solver_run_id,
                    "visualization": "floor_plan_scoring",
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                },
            )

    if settings.render_solver_attempts:
        try:
            _run_stage(
                context,
                GenerationStage.VISUALIZATION,
                lambda: _render_solver_attempt(
                    context=context,
                    attempt=attempt,
                    last_refinement_profile_name=_profile_name(refinement_profiles[-1]),
                ),
                label=f"{attempt_label}.visualization",
            )
        except Exception as exc:
            _log_generation(
                context,
                "visualization_skipped",
                "WARNING",
                {
                    "search_trial_id": search_trial_id,
                    "solver_run_id": solver_run_id,
                    "visualization": "floor_plan_general",
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                },
            )

    check_cancellation()
    return attempt


def _build_result(
    *,
    context: ExecutionContext,
    attempt: _CompletedFloorPlanAttempt,
    settings: GenerationPipelineSettings,
) -> GenerationPipelineResult:
    def validate_final_result() -> None:
        if settings.require_final_critical_pass and not attempt.scoring.passed_critical:
            raise GenerationPipelineError(
                GenerationStage.FINAL_VALIDATION,
                "critical_validation_failed",
                "The selected floor plan failed one or more critical scoring checks.",
                {
                    "score": attempt.scoring.total_score,
                    "search_trial_id": attempt.search_trial_id,
                    "solver_run_id": attempt.solver_run_id,
                },
            )

    _run_stage(
        context,
        GenerationStage.FINAL_VALIDATION,
        validate_final_result,
        summary=lambda _: "passed=true",
    )

    result = GenerationPipelineResult(
        floor_plan=deepcopy(attempt.final_floor_plan),
        scoring=attempt.scoring,
        execution_context=context.with_stage(PipelineStage.FINALIZATION),
    )
    try:
        save_final_floor_plan(
            context.with_stage(PipelineStage.FINALIZATION),
            result.floor_plan,
        )
    except Exception as exc:
        _log_generation(
            context,
            "final_artifact_failed",
            "WARNING",
            {"error_type": type(exc).__name__, "message": str(exc)},
        )
    return result


def run_generation_pipeline(
    request: GenerationPipelineRequest,
    *,
    settings: GenerationPipelineSettings = GenerationPipelineSettings(),
    events: GenerationEventPublisher | None = None,
    cancellation: GenerationCancellationSignal | None = None,
) -> GenerationPipelineResult:
    """
    Run the incremental candidate-search and floor-plan generation loop.

    The timeout is cooperative: it is checked between trials and solver runs.
    An already-running CP-SAT/refinement/post-processing operation is not forcibly
    interrupted by this orchestration layer.
    """

    pipeline_started = perf_counter()
    event_publisher = events or NullGenerationEventPublisher()
    execution_context = request.execution_context or create_pipeline_context(
        job_id=request.request_id,
        seed=settings.candidate_random_seed,
    )

    def check_cancellation() -> None:
        _raise_if_cancelled(
            cancellation=cancellation,
            context=execution_context,
            started=pipeline_started,
        )

    _log_generation(
        execution_context,
        "flow_started",
        data={"job_id": request.request_id},
    )
    event_publisher.status(GenerationStatus.JOB_STARTED)
    check_cancellation()

    def preprocess() -> PreparedGenerationInput:
        preprocessing_input = PreprocessingInput(
            request=PreprocessingRequest(
                floor_limits=FloorLimits(request.max_width, request.max_length),
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
            execution_context=execution_context.with_stage(
                PipelineStage.PREPROCESSING
            ),
        )
        return prepare_generation_input(preprocessing_input)

    prepared = _run_stage(
        execution_context,
        GenerationStage.PREPROCESSING,
        preprocess,
        expected_errors=(FloorPlanPreprocessingError,),
        summary=lambda value: f"rooms={len(value.generation_spec.rooms)}",
    )
    check_cancellation()
    specification = prepared.generation_spec
    if settings.candidate_search_enabled:
        event_publisher.status(GenerationStatus.CANDIDATE_SEARCH_STARTED)

    candidate_registry = create_candidate_scoring_registry()
    candidate_config = create_candidate_scoring_config()
    refinement_profiles = _load_refinement_profiles()
    latest_candidate_scoring: (
        tuple[
            CandidateScoringInput,
            CandidateScoringResult,
        ]
        | None
    ) = None
    active_scoring_context: ExecutionContext | None = None

    def score_candidate(points: tuple[Any, ...]) -> float:
        nonlocal latest_candidate_scoring
        check_cancellation()
        scoring_input = CandidateScoringInput(
            specification=specification,
            candidate=points,
            execution_context=active_scoring_context,
        )
        result = evaluate_candidate(
            scoring_input,
            registry=candidate_registry,
            config=candidate_config,
        )
        check_cancellation()
        latest_candidate_scoring = (scoring_input, result)
        return result.total_score

    best_usable_attempt: _CompletedFloorPlanAttempt | None = None
    best_usable_event_sequence: int | None = None
    solver_failure_count = 0
    last_solver_failure: dict[str, str] | None = None
    eligible_candidate_count = 0
    termination_reason = "candidate_trials_exhausted"

    def run_solver_for_candidate(
        *,
        search_trial_id: int | None,
        candidate_id: int,
        candidate_score: float,
        candidate_hints: tuple[RoomPlacementHint, ...],
        candidate_context: ExecutionContext,
    ) -> GenerationPipelineResult | None:
        nonlocal best_usable_attempt
        nonlocal best_usable_event_sequence
        nonlocal last_solver_failure
        nonlocal solver_failure_count
        nonlocal termination_reason

        event_publisher.status(GenerationStatus.FLOOR_PLAN_GENERATION_STARTED)
        max_runs = settings.effective_solver_runs_per_candidate
        for solver_run_number in range(1, max_runs + 1):
            check_cancellation()
            if _timed_out(pipeline_started, settings):
                termination_reason = "timeout"
                return None

            solver_context = candidate_context.for_solver_run(solver_run_number)
            _log_generation(
                solver_context,
                "solver_run_started",
                data={
                    "search_trial_id": search_trial_id,
                    "candidate_score": candidate_score,
                    "solver_run_id": solver_run_number,
                    "max_solver_runs": max_runs,
                },
            )

            try:
                attempt = _execute_solver_run(
                    request=request,
                    specification=specification,
                    search_trial_id=search_trial_id,
                    candidate_id=candidate_id,
                    candidate_score=candidate_score,
                    candidate_hints=candidate_hints,
                    solver_run_id=solver_run_number,
                    refinement_profiles=refinement_profiles,
                    settings=settings,
                    context=solver_context,
                    check_cancellation=check_cancellation,
                )
            except GenerationPipelineError as exc:
                if exc.details.get("termination_reason") == "cancelled":
                    raise
                solver_failure_count += 1
                last_solver_failure = {
                    "stage": exc.stage.value,
                    "code": exc.code,
                    "message": exc.message,
                }
                _log_generation(
                    solver_context,
                    "solver_run_failed",
                    "WARNING",
                    {
                        "search_trial_id": search_trial_id,
                        "solver_run_id": solver_run_number,
                        "stage": exc.stage.value,
                        "code": exc.code,
                        "will_retry_same_candidate": solver_run_number < max_runs,
                    },
                )
                continue

            check_cancellation()
            _log_generation(
                solver_context,
                "solver_run_scored",
                data={
                    "search_trial_id": search_trial_id,
                    "solver_run_id": solver_run_number,
                    "floor_plan_score": attempt.scoring.total_score,
                    "passed_critical": attempt.scoring.passed_critical,
                },
            )

            if _is_presentable(attempt, settings):
                _log_generation(
                    solver_context,
                    "presentable_floor_plan_found",
                    data={
                        "search_trial_id": search_trial_id,
                        "solver_run_id": solver_run_number,
                        "score": attempt.scoring.total_score,
                        "threshold": (settings.effective_presentable_floor_plan_score),
                    },
                )
                result = _build_result(
                    context=solver_context,
                    attempt=attempt,
                    settings=settings,
                )
                event_publisher.status(
                    GenerationStatus.PRESENTABLE_FLOOR_PLAN_FOUND
                )
                final_sequence = event_publisher.floor_plan(
                    classification=FloorPlanClassification.PRESENTABLE,
                    trial_number=(
                        attempt.search_trial_id + 1
                        if attempt.search_trial_id is not None
                        else None
                    ),
                    candidate_id=attempt.candidate_id,
                    solver_run_id=attempt.solver_run_id,
                    score=attempt.scoring.total_score,
                    passed_critical=attempt.scoring.passed_critical,
                    floor_plan=result.floor_plan,
                )
                event_publisher.completed(
                    outcome=CompletionOutcome.PRESENTABLE_PLAN_FOUND,
                    final_floor_plan_sequence=final_sequence,
                    elapsed_ms=round(_elapsed_seconds(pipeline_started) * 1000),
                )
                return result

            if _is_usable(attempt, settings):
                if _is_better_attempt(attempt, best_usable_attempt):
                    best_usable_attempt = attempt
                    _log_generation(
                        solver_context,
                        "usable_floor_plan_saved",
                        data={
                            "search_trial_id": search_trial_id,
                            "solver_run_id": solver_run_number,
                            "score": attempt.scoring.total_score,
                        },
                    )
                    event_publisher.status(
                        GenerationStatus.USABLE_FLOOR_PLAN_FOUND
                    )
                    best_usable_event_sequence = event_publisher.floor_plan(
                        classification=FloorPlanClassification.USABLE,
                        trial_number=(
                            attempt.search_trial_id + 1
                            if attempt.search_trial_id is not None
                            else None
                        ),
                        candidate_id=attempt.candidate_id,
                        solver_run_id=attempt.solver_run_id,
                        score=attempt.scoring.total_score,
                        passed_critical=attempt.scoring.passed_critical,
                        floor_plan=attempt.final_floor_plan,
                    )

                # A usable but not presentable plan causes another FPG run with
                # the same hints while runs remain.
                if _timed_out(pipeline_started, settings):
                    termination_reason = "timeout"
                    return None
                continue

            # A completed floor plan below the usable threshold immediately
            # abandons this hint and resumes candidate search.
            _log_generation(
                solver_context,
                "floor_plan_below_usable_threshold",
                data={
                    "search_trial_id": search_trial_id,
                    "solver_run_id": solver_run_number,
                    "score": attempt.scoring.total_score,
                    "usable_threshold": settings.usable_floor_plan_score,
                    "passed_critical": attempt.scoring.passed_critical,
                },
            )
            break

        return None

    if not settings.candidate_search_enabled:
        check_cancellation()
        default_context = execution_context.for_candidate(1)
        result = run_solver_for_candidate(
            search_trial_id=None,
            candidate_id=1,
            candidate_score=0.0,
            candidate_hints=_default_candidate_hints(specification),
            candidate_context=default_context,
        )
        if result is not None:
            return result
        termination_reason = (
            "timeout"
            if _timed_out(pipeline_started, settings)
            else "default_candidate_exhausted"
        )
    else:
        candidate_search_settings = CandidateSearchSettings(
            min_x=0.0,
            max_x=specification.floor.width,
            min_y=0.0,
            max_y=specification.floor.length,
            grid_resolution=settings.candidate_grid_resolution,
            trial_count=settings.candidate_trial_count,
            random_seed=settings.candidate_random_seed,
        )
        search_session = CandidateSearchSession(
            CandidateSearchInput(
                targets=tuple(
                    CandidateSearchTarget(room.id) for room in specification.rooms
                ),
                settings=candidate_search_settings,
                evaluator=score_candidate,
                execution_context=execution_context.with_stage(
                    PipelineStage.CANDIDATE_SEARCH
                ),
            )
        )

        while search_session.has_remaining_trials:
            check_cancellation()
            if _timed_out(pipeline_started, settings):
                termination_reason = "timeout"
                break

            suggestion = _run_stage(
                execution_context,
                GenerationStage.CANDIDATE_SEARCH,
                search_session.ask_next_trial,
                expected_errors=(TypeError, ValueError, RuntimeError),
                summary=lambda value: f"trial={value.trial_number}",
                label=(
                    f"candidate-trial-{search_session.completed_trials + 1}.generate"
                ),
            )
            check_cancellation()

            try:
                trial_context = execution_context.for_search_trial(
                    suggestion.trial_number
                )
                active_scoring_context = trial_context.with_stage(
                    PipelineStage.CANDIDATE_SCORING
                )
                trial_result = _run_stage(
                    trial_context,
                    GenerationStage.CANDIDATE_SCORING,
                    lambda: search_session.record_score(
                        suggestion,
                        score_candidate(suggestion.points),
                    ),
                    expected_errors=(TypeError, ValueError, RuntimeError),
                    summary=lambda value: (
                        f"trial={value.trial_number} score={value.score:.2f}"
                    ),
                    label=f"candidate-trial-{suggestion.trial_number}.score",
                )
            except Exception:
                search_session.fail_pending_trial()
                raise

            check_cancellation()
            event_publisher.candidate_trial(
                trial_number=trial_result.completed_trials,
                trial_limit=settings.candidate_trial_count,
                candidate_hints=trial_result.points,
            )
            event_publisher.progress(
                stage=GenerationStage.CANDIDATE_SEARCH.value,
                trial_number=trial_result.completed_trials,
                trial_limit=settings.candidate_trial_count,
                elapsed_ms=round(_elapsed_seconds(pipeline_started) * 1000),
                timeout_ms=round(settings.timeout_seconds * 1000),
            )

            if trial_result.score < settings.candidate_score_threshold:
                latest_candidate_scoring = None
                _log_generation(
                    trial_context,
                    "candidate_rejected",
                    data={
                        "trial_number": trial_result.trial_number,
                        "candidate_score": trial_result.score,
                        "threshold": settings.candidate_score_threshold,
                    },
                )
                continue

            eligible_candidate_count += 1
            candidate_context = trial_context.for_candidate(
                eligible_candidate_count
            )
            if latest_candidate_scoring is None:
                raise RuntimeError(
                    "Candidate scoring completed without retaining its result."
                )
            scoring_input, candidate_scoring_result = latest_candidate_scoring
            latest_candidate_scoring = None
            _log_generation(
                candidate_context,
                "candidate_eligible",
                data={
                    "trial_number": trial_result.trial_number,
                    "candidate_score": trial_result.score,
                    "threshold": settings.candidate_score_threshold,
                },
            )

            if settings.render_candidate_search:
                try:
                    _run_stage(
                        candidate_context,
                        GenerationStage.VISUALIZATION,
                        lambda: _render_candidate_trial(
                            context=candidate_context,
                            trial=trial_result,
                            settings=candidate_search_settings,
                        ),
                        label=(
                            f"candidate-trial-{trial_result.trial_number}.visualization"
                        ),
                    )
                except Exception as exc:
                    _log_generation(
                        candidate_context,
                        "visualization_skipped",
                        "WARNING",
                        {
                            "trial_number": trial_result.trial_number,
                            "visualization": "candidate_search",
                            "error_type": type(exc).__name__,
                            "message": str(exc),
                        },
                    )

            if settings.scoring_visualization.enabled:
                try:
                    _run_stage(
                        candidate_context,
                        GenerationStage.VISUALIZATION,
                        lambda: _render_candidate_scoring(
                            context=trial_context.with_stage(
                                PipelineStage.CANDIDATE_SCORING
                            ),
                            scoring_input=scoring_input,
                            scoring_result=candidate_scoring_result,
                            settings=settings,
                        ),
                        label=(
                            f"candidate-trial-{trial_result.trial_number}"
                            ".scoring_visualization"
                        ),
                    )
                except Exception as exc:
                    _log_generation(
                        candidate_context,
                        "visualization_skipped",
                        "WARNING",
                        {
                            "trial_number": trial_result.trial_number,
                            "visualization": "candidate_scoring",
                            "error_type": type(exc).__name__,
                            "message": str(exc),
                        },
                    )

            check_cancellation()
            result = run_solver_for_candidate(
                search_trial_id=trial_result.trial_number,
                candidate_id=eligible_candidate_count,
                candidate_score=trial_result.score,
                candidate_hints=_candidate_hints(trial_result),
                candidate_context=candidate_context,
            )
            check_cancellation()
            if result is not None:
                return result

            if _timed_out(pipeline_started, settings):
                termination_reason = "timeout"
                break

        if not search_session.has_remaining_trials and termination_reason != "timeout":
            termination_reason = "candidate_trials_exhausted"

    check_cancellation()
    if best_usable_attempt is not None:
        if termination_reason == "timeout":
            event_publisher.status(GenerationStatus.TIMEOUT_REACHED)
        _log_generation(
            execution_context,
            "returning_best_usable_floor_plan",
            data={
                "termination_reason": termination_reason,
                "score": best_usable_attempt.scoring.total_score,
                "search_trial_id": best_usable_attempt.search_trial_id,
                "solver_run_id": best_usable_attempt.solver_run_id,
                "elapsed_seconds": _elapsed_seconds(pipeline_started),
            },
        )
        result = _build_result(
            context=(
                execution_context.for_search_trial(
                    best_usable_attempt.search_trial_id
                )
                if best_usable_attempt.search_trial_id is not None
                else execution_context
            )
            .for_candidate(best_usable_attempt.candidate_id)
            .for_solver_run(best_usable_attempt.solver_run_id),
            attempt=best_usable_attempt,
            settings=settings,
        )
        event_publisher.completed(
            outcome=CompletionOutcome.BEST_USABLE_PLAN_RETURNED,
            final_floor_plan_sequence=best_usable_event_sequence,
            elapsed_ms=round(_elapsed_seconds(pipeline_started) * 1000),
        )
        return result

    raise GenerationPipelineError(
        GenerationStage.FINAL_VALIDATION,
        "no_floor_plan_found",
        "No usable floor plan was found before the pipeline stopped.",
        {
            "termination_reason": termination_reason,
            "timeout_seconds": settings.timeout_seconds,
            "elapsed_seconds": _elapsed_seconds(pipeline_started),
            "eligible_candidate_count": eligible_candidate_count,
            "solver_failure_count": solver_failure_count,
            "last_solver_failure": last_solver_failure,
        },
    )

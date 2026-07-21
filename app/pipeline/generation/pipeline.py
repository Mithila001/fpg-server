# app/pipeline/generation/pipeline.py
from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from inspect import signature
from math import ceil, sqrt
from time import perf_counter
from typing import Any, TypeVar, cast

import app.algorithms.floor_plan_solver as floor_plan_solver_module
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
    FloorPlanScoringResult,
    score_floor_plan,
)
from app.algorithms.floor_plan_solver import (
    INITIAL_GENERATION_PROFILE,
    FloorPlanSolveRequest,
    FloorPlanSolverError,
    RoomPlacementHint,
    generate_floor_plan,
)
from app.algorithms.types_new import FloorPlan
from app.visualization.api import (
    FloorPlanFlowVisualization,
    FloorPlanVisualizationStage,
    render_floor_plan_general,
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
class _SuccessfulSolverAttempt:
    attempt_number: int
    initial_floor_plan: FloorPlan
    refined_floor_plan: FloorPlan
    post_processed_floor_plan: FloorPlan
    scoring: FloorPlanScoringResult


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
    label: str | None = None,
) -> T:
    started = perf_counter()
    stage_label = label or stage.value
    print(f"[generation:{request_id}] {stage_label} started")
    try:
        result = operation()
    except GenerationPipelineError as exc:
        duration_ms = (perf_counter() - started) * 1000
        print(
            f"[generation:{request_id}] {stage_label} failed "
            f"code={exc.code} duration_ms={duration_ms:.1f}: {exc.message}"
        )
        raise
    except expected_errors as exc:
        duration_ms = (perf_counter() - started) * 1000
        error = GenerationPipelineError(stage, _error_code(exc), str(exc))
        print(
            f"[generation:{request_id}] {stage_label} failed "
            f"code={error.code} duration_ms={duration_ms:.1f}: {error.message}"
        )
        raise error from exc
    except Exception as exc:
        duration_ms = (perf_counter() - started) * 1000
        print(
            f"[generation:{request_id}] {stage_label} failed "
            f"code=unexpected_error duration_ms={duration_ms:.1f}: {exc}"
        )
        raise

    duration_ms = (perf_counter() - started) * 1000
    suffix = f" {summary(result)}" if summary is not None else ""
    print(
        f"[generation:{request_id}] {stage_label} completed "
        f"duration_ms={duration_ms:.1f}{suffix}"
    )
    return result


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
) -> FloorPlanSolveRequest:
    request_arguments: dict[str, Any] = {
        "specification": specification,
        "profile": profile,
        "candidate_hints": candidate_hints,
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
    vertical_step = specification.floor.height / (rows + 1)

    return tuple(
        RoomPlacementHint(
            room.id,
            (index % columns + 1) * horizontal_step,
            (index // columns + 1) * vertical_step,
        )
        for index, room in enumerate(specification.rooms)
    )


def _candidate_seed(base_seed: int | None, attempt_number: int) -> int | None:
    if base_seed is None:
        return None
    return base_seed + attempt_number - 1


def _is_better_attempt(
    candidate: _SuccessfulSolverAttempt,
    current_best: _SuccessfulSolverAttempt | None,
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


def _target_reached(
    scoring: FloorPlanScoringResult,
    target_score: float | None,
) -> bool:
    return (
        target_score is not None
        and scoring.passed_critical
        and scoring.total_score >= target_score
    )


def _render_solver_attempt(
    *,
    request_id: str,
    attempt: _SuccessfulSolverAttempt,
    last_refinement_profile_name: str,
) -> None:
    payload = FloorPlanFlowVisualization(
        stages=(
            FloorPlanVisualizationStage(
                stage_id=f"attempt-{attempt.attempt_number}-initial",
                stage_name="Initial Generation",
                category="solver",
                profile_name=_profile_name(INITIAL_GENERATION_PROFILE),
                floor_plan=deepcopy(attempt.initial_floor_plan),
            ),
            FloorPlanVisualizationStage(
                stage_id=f"attempt-{attempt.attempt_number}-last-refined",
                stage_name="Last Refined Generation",
                category="solver_refinement",
                profile_name=last_refinement_profile_name,
                floor_plan=deepcopy(attempt.refined_floor_plan),
            ),
            FloorPlanVisualizationStage(
                stage_id=f"attempt-{attempt.attempt_number}-post-processed",
                stage_name="Post Processed Floor Plan",
                category="post_processing",
                profile_name=_profile_name(POST_PROCESSING_PROFILE),
                floor_plan=deepcopy(attempt.post_processed_floor_plan),
            ),
        )
    )
    render_floor_plan_general(
        payload,
        run_id=request_id,
        output_prefix=f"solver-attempt-{attempt.attempt_number}",
    )


def run_generation_pipeline(
    request: GenerationPipelineRequest,
    *,
    settings: GenerationPipelineSettings = GenerationPipelineSettings(),
) -> GenerationPipelineResult:
    """Run the modular generation features with bounded retry orchestration."""

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
    refinement_profiles = _load_refinement_profiles()
    last_refinement_profile_name = _profile_name(refinement_profiles[-1])

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

    best_attempt: _SuccessfulSolverAttempt | None = None
    attempt_failures: list[dict[str, Any]] = []

    for attempt_number in range(1, settings.solver_max_attempts + 1):
        attempt_label = f"attempt-{attempt_number}"
        print(
            f"[generation:{request.request_id}] {attempt_label} started "
            f"max_attempts={settings.solver_max_attempts}"
        )

        try:
            if settings.candidate_search_enabled:
                search_result = _run_stage(
                    request.request_id,
                    GenerationStage.CANDIDATE_SEARCH,
                    lambda: search_candidates(
                        CandidateSearchInput(
                            targets=tuple(
                                CandidateSearchTarget(room.id)
                                for room in specification.rooms
                            ),
                            settings=CandidateSearchSettings(
                                min_x=0.0,
                                max_x=specification.floor.width,
                                min_y=0.0,
                                max_y=specification.floor.height,
                                grid_resolution=settings.candidate_grid_resolution,
                                trial_count=settings.candidate_trial_count,
                                random_seed=_candidate_seed(
                                    settings.candidate_random_seed,
                                    attempt_number,
                                ),
                            ),
                            evaluator=score_candidate,
                        )
                    ),
                    expected_errors=(TypeError, ValueError, RuntimeError),
                    summary=lambda value: (
                        f"score={value.score:.2f} trials={value.completed_trials}"
                    ),
                    label=f"{attempt_label}.candidate_search",
                )
                candidate_hints = tuple(
                    RoomPlacementHint(point.room_id, point.x, point.y)
                    for point in search_result.points
                )
            else:
                candidate_hints = _default_candidate_hints(specification)

            def solve_initial():
                result = generate_floor_plan(
                    _create_solver_request(
                        specification=specification,
                        profile=INITIAL_GENERATION_PROFILE,
                        candidate_hints=candidate_hints,
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
                request.request_id,
                GenerationStage.SOLVER,
                solve_initial,
                expected_errors=(FloorPlanSolverError,),
                summary=lambda value: f"status={value.status.value}",
                label=f"{attempt_label}.initial_generation",
            )
            current_floor_plan = cast(FloorPlan, initial_result.floor_plan)
            initial_floor_plan = deepcopy(current_floor_plan)

            for refinement_index, profile in enumerate(refinement_profiles, start=1):
                profile_name = _profile_name(profile)

                def refine(
                    active_profile: Any = profile,
                    source_floor_plan: FloorPlan = current_floor_plan,
                ):
                    result = generate_floor_plan(
                        _create_solver_request(
                            specification=specification,
                            profile=active_profile,
                            candidate_hints=candidate_hints,
                            floor_plan=source_floor_plan,
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
                    request.request_id,
                    GenerationStage.REFINEMENT,
                    refine,
                    expected_errors=(FloorPlanSolverError,),
                    summary=lambda value: f"status={value.status.value}",
                    label=(
                        f"{attempt_label}.refinement-{refinement_index}"
                        f"[{profile_name}]"
                    ),
                )
                current_floor_plan = cast(
                    FloorPlan, refinement_result.floor_plan
                )

            refined_floor_plan = deepcopy(current_floor_plan)
            attempt_scoring = _run_stage(
                request.request_id,
                GenerationStage.ATTEMPT_SCORING,
                lambda: score_floor_plan(refined_floor_plan, specification),
                expected_errors=(FloorPlanScoringError,),
                summary=lambda value: (
                    f"score={value.total_score:.2f} "
                    f"passed_critical={value.passed_critical}"
                ),
                label=f"{attempt_label}.scoring",
            )

            def post_process():
                result = post_process_floor_plan(
                    PostProcessingRequest(
                        floor_plan=refined_floor_plan,
                        profile=POST_PROCESSING_PROFILE,
                        specification=specification,
                        request_id=f"{request.request_id}-{attempt_label}",
                    )
                )
                if result.status is PipelineStatus.FAILED:
                    failure = result.failure
                    raise GenerationPipelineError(
                        GenerationStage.POST_PROCESSING,
                        failure.code if failure else "post_processing_failed",
                        (
                            failure.message
                            if failure
                            else "Floor-plan post-processing failed."
                        ),
                        {"executions": result.executions},
                    )
                return result

            post_result = _run_stage(
                request.request_id,
                GenerationStage.POST_PROCESSING,
                post_process,
                summary=lambda value: f"rooms={len(value.floor_plan.rooms)}",
                label=f"{attempt_label}.post_processing",
            )

            successful_attempt = _SuccessfulSolverAttempt(
                attempt_number=attempt_number,
                initial_floor_plan=initial_floor_plan,
                refined_floor_plan=refined_floor_plan,
                post_processed_floor_plan=deepcopy(post_result.floor_plan),
                scoring=attempt_scoring,
            )

            if settings.render_solver_attempts:
                try:
                    _run_stage(
                        request.request_id,
                        GenerationStage.VISUALIZATION,
                        lambda: _render_solver_attempt(
                            request_id=request.request_id,
                            attempt=successful_attempt,
                            last_refinement_profile_name=(
                                last_refinement_profile_name
                            ),
                        ),
                        label=f"{attempt_label}.visualization",
                    )
                except Exception as exc:
                    print(
                        f"[generation:{request.request_id}] "
                        f"{attempt_label}.visualization skipped: {exc}"
                    )

            if _is_better_attempt(successful_attempt, best_attempt):
                best_attempt = successful_attempt
                print(
                    f"[generation:{request.request_id}] {attempt_label} "
                    f"saved_as_best score={attempt_scoring.total_score:.2f}"
                )

            if _target_reached(
                attempt_scoring,
                settings.target_floor_plan_score,
            ):
                print(
                    f"[generation:{request.request_id}] target score reached "
                    f"on {attempt_label}; stopping solver loop"
                )
                break

        except GenerationPipelineError as exc:
            attempt_failures.append(
                {
                    "attempt_number": attempt_number,
                    "stage": exc.stage.value,
                    "code": exc.code,
                    "message": exc.message,
                    "details": dict(exc.details),
                }
            )
            print(
                f"[generation:{request.request_id}] {attempt_label} failed; "
                "continuing when attempts remain"
            )
            continue

    if best_attempt is None:
        raise GenerationPipelineError(
            GenerationStage.SOLVER,
            "solver_attempts_exhausted",
            "All solver attempts failed before producing a usable floor plan.",
            {
                "max_attempts": settings.solver_max_attempts,
                "attempt_failures": tuple(attempt_failures),
            },
        )

    def add_openings():
        result = generate_openings(
            OpeningGenerationRequest(
                floor_plan=best_attempt.post_processed_floor_plan,
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
        if result.floor_plan is None:
            raise GenerationPipelineError(
                GenerationStage.OPENINGS,
                "openings_missing_floor_plan",
                "Opening generation reported success without returning a floor plan.",
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
    opened_floor_plan = cast(FloorPlan, opening_result.floor_plan)

    final_scoring = _run_stage(
        request.request_id,
        GenerationStage.SCORING,
        lambda: score_floor_plan(opened_floor_plan, specification),
        expected_errors=(FloorPlanScoringError,),
        summary=lambda value: (
            f"score={value.total_score:.2f} passed_critical={value.passed_critical}"
        ),
    )

    def validate_final_result() -> None:
        if settings.require_final_critical_pass and not final_scoring.passed_critical:
            raise GenerationPipelineError(
                GenerationStage.FINAL_VALIDATION,
                "critical_validation_failed",
                "The final floor plan failed one or more critical scoring checks.",
                {
                    "score": final_scoring.total_score,
                    "best_solver_attempt": best_attempt.attempt_number,
                },
            )

    _run_stage(
        request.request_id,
        GenerationStage.FINAL_VALIDATION,
        validate_final_result,
        summary=lambda _: "passed=true",
    )

    return GenerationPipelineResult(
        floor_plan=opened_floor_plan,
        scoring=final_scoring,
    )

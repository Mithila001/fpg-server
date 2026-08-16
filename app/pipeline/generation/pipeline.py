from __future__ import annotations

import json
import os
from dataclasses import dataclass, replace
from pathlib import Path
from time import monotonic
from typing import Any, Callable

from fpg_core.candidate_circulation import (
    CandidateCirculationInput,
    refine_candidate_circulation,
)
from fpg_core.candidate_scoring import (
    CandidateScoringInput,
    ScoringResult,
    evaluate_candidate,
)
from fpg_core.candidate_scoring import (
    create_default_registry as create_candidate_scoring_registry,
)
from fpg_core.candidate_search import (
    CandidateSearchInput,
    CandidateSearchSession,
    build_candidate_search_targets,
)
from fpg_core.domain import CandidateMap, ExecutionMode, FloorPlan
from fpg_core.floor_plan_openings import (
    OpeningGenerationRequest,
    generate_openings,
)
from fpg_core.floor_plan_post_processing import (
    PipelineStatus,
    PostProcessingRequest,
    post_process_floor_plan,
)
from fpg_core.floor_plan_preprocessing import (
    FloorLimits,
    PreprocessingInput,
    PreprocessingRequest,
    RequestedRoom,
    prepare_generation_input,
)
from fpg_core.floor_plan_scoring import (
    FloorPlanScoringInput,
    FloorPlanScoringResult,
    score_floor_plan,
)
from fpg_core.floor_plan_solver import (
    FloorPlanSolveRequest,
    RoomPlacementHint,
    SolverStatus,
    generate_floor_plan,
)

from app.artifacts.serializers import to_json_value
from app.core_config import ServerConfig
from app.streaming import (
    EventError,
    EventType,
    GenerationEventPublisher,
    WorkerEvent,
)

from .context import (
    CancellationSignal,
    GenerationPipelineError,
    GenerationPipelineRequest,
    GenerationPipelineResult,
    GenerationStage,
)


@dataclass(frozen=True, slots=True)
class _Attempt:
    floor_plan: FloorPlan
    scoring: FloorPlanScoringResult
    trial_number: int
    candidate_id: int


def _publish(
    publisher: GenerationEventPublisher,
    event_type: EventType,
    stage: GenerationStage,
    state: str,
    message: str,
    *,
    data: dict[str, Any] | None = None,
    error: EventError | None = None,
    trial_number: int | None = None,
    candidate_id: int | None = None,
) -> None:
    publisher.publish(
        WorkerEvent(
            event_type=event_type,
            stage=stage.value,
            state=state,
            message=message,
            data=data or {},
            error=error,
            trial_number=trial_number,
            candidate_id=candidate_id,
        )
    )


def _save_json(path: Path, value: Any, output_root: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.p{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(to_json_value(value), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)
    return path.resolve().relative_to(output_root.resolve()).as_posix()


def _hints(candidate: CandidateMap) -> tuple[RoomPlacementHint, ...]:
    return tuple(
        RoomPlacementHint(room_id=point.room_id, x=point.x, y=point.y)
        for point in candidate.points
    )


def run_generation_pipeline(
    request: GenerationPipelineRequest,
    config: ServerConfig,
    publisher: GenerationEventPublisher,
    cancellation: CancellationSignal,
) -> GenerationPipelineResult:
    started = monotonic()
    deadline = started + config.server.request_timeout_seconds

    def remaining() -> float:
        return max(0.0, deadline - monotonic())

    def checkpoint(stage: GenerationStage) -> None:
        if cancellation.is_set():
            raise GenerationPipelineError(
                stage,
                "generation_cancelled",
                "Generation was cancelled.",
                {"termination_reason": "cancelled"},
            )
        if remaining() <= 0:
            raise GenerationPipelineError(
                stage,
                "generation_timed_out",
                "The configured generation deadline was reached.",
                {"termination_reason": "timeout"},
            )

    _publish(
        publisher,
        EventType.STAGE,
        GenerationStage.PREPROCESSING,
        "started",
        "Preprocessing",
    )
    checkpoint(GenerationStage.PREPROCESSING)
    try:
        preprocessing_config, floor_size_profile = (
            config.preprocessing_for_floor_limits(request.max_width, request.max_length)
        )
        preprocessing = prepare_generation_input(
            PreprocessingInput(
                request=PreprocessingRequest(
                    floor_limits=FloorLimits(request.max_width, request.max_length),
                    aspect_ratio=request.aspect_ratio,
                    rooms=tuple(
                        RequestedRoom(
                            room_type=room.room_type,
                            id=room.id,
                            name=room.name,
                            requested_size=room.requested_size,
                        )
                        for room in request.rooms
                    ),
                ),
                config=preprocessing_config,
            ),
            mode=ExecutionMode.PRODUCTION,
        )
    except Exception as exc:
        raise GenerationPipelineError(
            GenerationStage.PREPROCESSING,
            "preprocessing_failed",
            str(exc),
        ) from exc
    prepared = preprocessing.result
    _publish(
        publisher,
        EventType.STAGE,
        GenerationStage.PREPROCESSING,
        "completed",
        "Preprocessing complete",
        data={
            "floor_width": prepared.generation_spec.floor.width,
            "floor_length": prepared.generation_spec.floor.length,
            "floor_size_category": floor_size_profile.name,
            "floor_limit_area": floor_size_profile.floor_area,
            "circulation_ratio": floor_size_profile.circulation_ratio,
            "circulation_allowance_area": (
                floor_size_profile.circulation_allowance_area
            ),
            "max_hallway_room_count": (floor_size_profile.max_hallway_room_count),
        },
    )

    room_types = {room.room_type for room in prepared.generation_spec.rooms}
    circulation_config = config.circulation_for(room_types)
    candidate_scoring_config = config.candidate_scoring_for(circulation_config)
    scoring_registry = create_candidate_scoring_registry()
    flow_root = Path(request.flow_directory)

    def evaluate(
        candidate: CandidateMap, trial_number: int
    ) -> tuple[CandidateMap, ScoringResult, str]:
        checkpoint(GenerationStage.CANDIDATE_CIRCULATION)
        _publish(
            publisher,
            EventType.STAGE,
            GenerationStage.CANDIDATE_CIRCULATION,
            "started",
            "Filtering Hint Map",
            trial_number=trial_number,
        )
        circulation = refine_candidate_circulation(
            CandidateCirculationInput(
                candidate=candidate,
                config=circulation_config,
            ),
            mode=ExecutionMode.DEBUG,
        )
        artifact = _save_json(
            flow_root
            / "json"
            / "candidate_circulation"
            / f"trial-{trial_number:06d}.json",
            circulation,
            config.server.output_root,
        )
        candidate_spec = prepared.generation_spec_for_candidate(
            circulation.result.candidate
        )
        checkpoint(GenerationStage.CANDIDATE_SCORING)
        scoring = evaluate_candidate(
            CandidateScoringInput(
                specification=candidate_spec,
                candidate=circulation.result.candidate,
                hallway_classifications=circulation.result.hallway_classifications,
            ),
            registry=scoring_registry,
            config=candidate_scoring_config,
            mode=ExecutionMode.PRODUCTION,
        )
        return circulation.result.candidate, scoring, artifact

    search = CandidateSearchSession(
        CandidateSearchInput(
            targets=build_candidate_search_targets(prepared.generation_spec),
            grid=prepared.candidate_grid,
            hallway_room_count_range=prepared.hallway_room_count_range,
            evaluator=lambda candidate: 0.0,
            config=config.core.candidate_search,
        )
    )
    _publish(
        publisher,
        EventType.STAGE,
        GenerationStage.CANDIDATE_SEARCH,
        "started",
        "Searching Candidate",
        data={"trial_limit": config.core.candidate_search.trial_count},
    )

    best: _Attempt | None = None
    candidate_id = 0

    while search.has_remaining_trials:
        checkpoint(GenerationStage.CANDIDATE_SEARCH)
        suggestion = search.ask_next_trial()
        trial_number = suggestion.trial_number + 1
        _publish(
            publisher,
            EventType.CANDIDATE,
            GenerationStage.CANDIDATE_SEARCH,
            "generated",
            "Candidate hint map generated",
            data={"candidate_hints": to_json_value(suggestion.candidate.points)},
            trial_number=trial_number,
        )
        try:
            evaluated = evaluate(suggestion.candidate, trial_number)
            result = search.record_score(suggestion, evaluated[1].total_score)
        except Exception as exc:
            search.fail_pending_trial()
            _publish(
                publisher,
                EventType.ATTEMPT_ERROR,
                GenerationStage.CANDIDATE_CIRCULATION,
                "failed",
                "Candidate filtering or scoring failed",
                error=EventError(
                    code="candidate_evaluation_failed",
                    message=str(exc),
                    recoverable=True,
                ),
                trial_number=trial_number,
            )
            continue

        filtered_candidate, _candidate_score, artifact = evaluated
        accepted = result.score >= config.generation.candidate_score_threshold
        _publish(
            publisher,
            EventType.CANDIDATE,
            GenerationStage.CANDIDATE_SCORING,
            "accepted" if accepted else "rejected",
            "Candidate scored",
            data={
                "score": result.score,
                "threshold": config.generation.candidate_score_threshold,
                "accepted": accepted,
                "circulation_artifact": artifact,
            },
            trial_number=trial_number,
        )
        if not accepted:
            continue

        candidate_id += 1
        specification = prepared.generation_spec_for_candidate(filtered_candidate)
        for _solver_run in range(config.generation.solver_runs_per_candidate):
            checkpoint(GenerationStage.INITIAL_GENERATION)
            try:
                attempt = _generate_attempt(
                    specification=specification,
                    candidate=filtered_candidate,
                    config=config,
                    publisher=publisher,
                    checkpoint=checkpoint,
                    remaining=remaining,
                    trial_number=trial_number,
                    candidate_id=candidate_id,
                )
            except GenerationPipelineError as exc:
                if exc.details.get("termination_reason") is not None:
                    if best is not None:
                        raise GenerationPipelineError(
                            exc.stage,
                            exc.code,
                            exc.message,
                            {
                                **dict(exc.details),
                                "best_floor_plan": to_json_value(best.floor_plan),
                                "best_scoring": to_json_value(best.scoring),
                            },
                        ) from exc
                    raise
                _publish(
                    publisher,
                    EventType.ATTEMPT_ERROR,
                    exc.stage,
                    "failed",
                    exc.message,
                    error=EventError(
                        code=exc.code,
                        message=exc.message,
                        recoverable=True,
                        details=dict(exc.details),
                    ),
                    trial_number=trial_number,
                    candidate_id=candidate_id,
                )
                continue

            usable = (
                (
                    not config.generation.require_final_critical_pass
                    or attempt.scoring.passed_critical
                )
                and attempt.scoring.total_score
                >= config.generation.usable_floor_plan_score
            )
            if usable and (
                best is None or attempt.scoring.total_score > best.scoring.total_score
            ):
                best = attempt
            if usable and attempt.scoring.total_score >= (
                config.generation.presentable_floor_plan_score
            ):
                return GenerationPipelineResult(
                    floor_plan=attempt.floor_plan,
                    scoring=attempt.scoring,
                    classification="presentable",
                    outcome="presentable_plan_found",
                )

    if best is not None:
        return GenerationPipelineResult(
            floor_plan=best.floor_plan,
            scoring=best.scoring,
            classification="usable",
            outcome="best_usable_plan_returned",
        )
    raise GenerationPipelineError(
        GenerationStage.GENERATION,
        "no_usable_floor_plan",
        "Candidate trials were exhausted without a usable floor plan.",
        {"completed_trials": search.completed_trials},
    )


def _generate_attempt(
    *,
    specification: Any,
    candidate: CandidateMap,
    config: ServerConfig,
    publisher: GenerationEventPublisher,
    checkpoint: Callable[[GenerationStage], None],
    remaining: Callable[[], float],
    trial_number: int,
    candidate_id: int,
) -> _Attempt:
    profiles = config.core.floor_plan_solver
    plan: FloorPlan | None = None
    for stage, profile in (
        (GenerationStage.INITIAL_GENERATION, profiles.initial),
        (GenerationStage.REFINEMENT_A, profiles.refinement_a),
        (GenerationStage.REFINEMENT_B, profiles.refinement_b),
    ):
        checkpoint(stage)
        _publish(
            publisher,
            EventType.STAGE,
            stage,
            "started",
            "Generating Floor Plan"
            if plan is None
            else f"Refining Floor Plan: {stage.value}",
            trial_number=trial_number,
            candidate_id=candidate_id,
        )
        solver = replace(
            profile.solver,
            max_time_seconds=max(
                0.01, min(profile.solver.max_time_seconds, remaining())
            ),
        )
        active_profile = replace(profile, solver=solver)
        execution = generate_floor_plan(
            FloorPlanSolveRequest(
                specification=specification,
                config=active_profile,
                candidate_hints=_hints(candidate) if plan is None else (),
                existing_floor_plan=plan,
            ),
            mode=ExecutionMode.PRODUCTION,
        )
        if execution.result.status not in {SolverStatus.OPTIMAL, SolverStatus.FEASIBLE}:
            raise GenerationPipelineError(
                stage,
                "solver_infeasible",
                execution.result.message,
                {"solver_status": execution.result.status.value},
            )
        plan = execution.result.floor_plan
        if plan is None:
            raise GenerationPipelineError(
                stage, "solver_result_missing", "Solver returned no floor plan."
            )
        _publish(
            publisher,
            EventType.FLOOR_PLAN,
            stage,
            "completed",
            "Floor plan generated"
            if stage is GenerationStage.INITIAL_GENERATION
            else "Floor plan refined",
            data={"floor_plan": to_json_value(plan)},
            trial_number=trial_number,
            candidate_id=candidate_id,
        )

    assert plan is not None
    checkpoint(GenerationStage.POST_PROCESSING)
    _publish(
        publisher,
        EventType.STAGE,
        GenerationStage.POST_PROCESSING,
        "started",
        "Post Processing",
        trial_number=trial_number,
        candidate_id=candidate_id,
    )
    post = post_process_floor_plan(
        PostProcessingRequest(
            floor_plan=plan,
            config=config.core.post_processing,
            specification=specification,
        ),
        mode=ExecutionMode.PRODUCTION,
    )
    if post.result.status is not PipelineStatus.SUCCESS:
        failure = post.result.failure
        raise GenerationPipelineError(
            GenerationStage.POST_PROCESSING,
            failure.code if failure is not None else "post_processing_failed",
            failure.message if failure is not None else "Post-processing failed.",
        )
    checkpoint(GenerationStage.OPENINGS)
    _publish(
        publisher,
        EventType.STAGE,
        GenerationStage.OPENINGS,
        "started",
        "Generating Openings",
        trial_number=trial_number,
        candidate_id=candidate_id,
    )
    openings = generate_openings(
        OpeningGenerationRequest(
            floor_plan=post.result.floor_plan,
            config=config.core.openings,
        ),
        mode=ExecutionMode.PRODUCTION,
    )
    if not openings.result.solved or openings.result.floor_plan is None:
        raise GenerationPipelineError(
            GenerationStage.OPENINGS,
            "opening_generation_failed",
            openings.result.message,
            {"opening_status": openings.result.status.value},
        )
    final_plan = openings.result.floor_plan
    checkpoint(GenerationStage.FINAL_SCORING)
    _publish(
        publisher,
        EventType.STAGE,
        GenerationStage.FINAL_SCORING,
        "started",
        "Final Scoring",
        trial_number=trial_number,
        candidate_id=candidate_id,
    )
    scoring = score_floor_plan(
        FloorPlanScoringInput(
            floor_plan=final_plan,
            specification=specification,
            config=config.core.floor_plan_scoring,
        ),
        mode=ExecutionMode.PRODUCTION,
    ).result
    _publish(
        publisher,
        EventType.FLOOR_PLAN,
        GenerationStage.FINAL_SCORING,
        "completed",
        "Final floor plan scored",
        data={
            "floor_plan": to_json_value(final_plan),
            "score": scoring.total_score,
            "passed_critical": scoring.passed_critical,
        },
        trial_number=trial_number,
        candidate_id=candidate_id,
    )
    return _Attempt(final_plan, scoring, trial_number, candidate_id)

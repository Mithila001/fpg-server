from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from app.algorithms.candidate_scoring.logging import (
    CandidateScoringEvent,
    log_candidate_scoring_event,
)
from app.algorithms.candidate_search.logging import (
    CandidateSearchEvent,
    log_candidate_search_event,
)
from app.algorithms.floor_plan_openings.logging import (
    FloorPlanOpeningsEvent,
    log_openings_event,
)
from app.algorithms.floor_plan_post_processing.logging import (
    PostProcessingEvent,
    log_post_processing_event,
)
from app.algorithms.floor_plan_preprocessing.logging import (
    PreprocessingEvent,
    log_preprocessing_event,
)
from app.algorithms.floor_plan_scoring.logging import (
    FloorPlanScoringEvent,
    log_floor_plan_scoring_event,
)
from app.algorithms.floor_plan_solver.logging import (
    FloorPlanSolverEvent,
    log_solver_event,
)
from app.artifacts import (
    ArtifactFormat,
    ArtifactKind,
    ArtifactScope,
    ArtifactStorage,
    ArtifactStorageConfig,
    ArtifactWriteRequest,
    FeatureKey,
    WriteMode,
)
from app.pipeline.generation.logging import log_pipeline_event

PNG = b"\x89PNG\r\n\x1a\nobservability-test"


def test_one_flow_groups_feature_events_and_matching_artifacts(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("OUTPUT_ROOT", str(tmp_path))
    storage = ArtifactStorage(ArtifactStorageConfig(output_root=tmp_path))
    root = storage.create_execution_context(
        job_id="external-job",
        started_at=datetime(2026, 7, 26, 12, 30, 45, 195000, tzinfo=UTC),
    )
    trial = root.for_search_trial(0)
    candidate = trial.for_candidate(1)
    solver = candidate.for_solver_run(1)

    log_pipeline_event(root, "flow_started")
    log_preprocessing_event(root, PreprocessingEvent.COMPLETED)
    log_candidate_search_event(trial, CandidateSearchEvent.TRIAL_COMPLETED)
    log_candidate_scoring_event(trial, CandidateScoringEvent.COMPLETED)
    log_solver_event(solver, FloorPlanSolverEvent.COMPLETED)
    log_post_processing_event(
        solver,
        PostProcessingEvent.COMPLETED.value,
        "INFO",
    )
    log_openings_event(solver, FloorPlanOpeningsEvent.COMPLETED)
    log_floor_plan_scoring_event(solver, FloorPlanScoringEvent.COMPLETED)

    json_reference = storage.save_json(
        ArtifactWriteRequest(
            feature=FeatureKey.FLOOR_PLAN_SOLVER,
            artifact_kind=ArtifactKind.FLOOR_PLAN_DATA,
            artifact_format=ArtifactFormat.JSON,
            artifact_scope=ArtifactScope.SOLVER_RUN,
            semantic_name="floor_plan",
            execution_context=solver,
            write_mode=WriteMode.REPLACE,
        ),
        {"solved": True},
    )
    png_reference = storage.save_png(
        ArtifactWriteRequest(
            feature=FeatureKey.FLOOR_PLAN_SOLVER,
            artifact_kind=ArtifactKind.VISUALIZATION,
            artifact_format=ArtifactFormat.PNG,
            artifact_scope=ArtifactScope.SOLVER_RUN,
            semantic_name="floor_plan",
            execution_context=solver,
            write_mode=WriteMode.REPLACE,
        ),
        PNG,
    )

    flow_root = next((tmp_path / "flows").iterdir())
    assert {item.name for item in flow_root.iterdir()} == {"json", "png"}
    assert json_reference.path is not None and png_reference.path is not None
    assert json_reference.path.stem == png_reference.path.stem
    event_files = tuple((flow_root / "json" / "logs").rglob("*.json"))
    assert len(event_files) == 8
    flow_ids = {
        json.loads(path.read_text())["execution_context"]["flow_id"]
        for path in event_files
    }
    assert flow_ids == {str(root.flow_id)}
    assert not tuple(flow_root.rglob("*.lock"))
    assert not tuple(flow_root.rglob("*.tmp"))

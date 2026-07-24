from __future__ import annotations

from types import SimpleNamespace

import pytest

import app.pipeline.generation.pipeline as pipeline_module
from app.algorithms.types_new import FloorPlan, Point, Polygon, RoomType
from app.pipeline.generation.context import (
    GenerationPipelineError,
    GenerationPipelineRequest,
    GenerationPipelineSettings,
    GenerationStage,
    RequestedGenerationRoom,
)


def _request() -> GenerationPipelineRequest:
    return GenerationPipelineRequest(
        request_id="pipeline-diagnostics-test",
        max_width=120,
        max_length=100,
        aspect_ratio="1:1",
        rooms=(
            RequestedGenerationRoom(RoomType.BEDROOM, id="bedroom"),
            RequestedGenerationRoom(RoomType.KITCHEN, id="kitchen"),
            RequestedGenerationRoom(RoomType.BATHROOM, id="bathroom"),
            RequestedGenerationRoom(RoomType.VERANDA, id="veranda"),
        ),
    )


def test_no_floor_plan_error_summarizes_solver_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_solver_run(**_kwargs):
        raise GenerationPipelineError(
            GenerationStage.SOLVER,
            "solver_infeasible",
            "The selected profile produced an infeasible model",
            {"diagnostics": {"large": "internal payload"}},
        )

    monkeypatch.setattr(
        pipeline_module,
        "_execute_solver_run",
        fail_solver_run,
    )

    with pytest.raises(GenerationPipelineError) as captured:
        pipeline_module.run_generation_pipeline(
            _request(),
            settings=GenerationPipelineSettings(
                candidate_search_enabled=False,
                solver_runs_per_candidate=2,
                render_candidate_search=False,
                render_solver_attempts=False,
            ),
        )

    details = dict(captured.value.details)
    assert details["solver_failure_count"] == 2
    assert details["last_solver_failure"] == {
        "stage": "solver",
        "code": "solver_infeasible",
        "message": "The selected profile produced an infeasible model",
    }
    assert "solver_failures" not in details
    assert "diagnostics" not in str(details)


def test_solver_visualization_uses_initial_refined_and_final_stages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    def capture(payload, **_kwargs):
        captured["payload"] = payload

    monkeypatch.setattr(pipeline_module, "render_floor_plan_general", capture)
    plans = tuple(
        FloorPlan(
            boundary=Polygon(
                (
                    Point(0, 0),
                    Point(size, 0),
                    Point(size, size),
                    Point(0, size),
                )
            ),
            rooms=[],
        )
        for size in (10, 11, 12, 13)
    )
    attempt = SimpleNamespace(
        candidate_trial_number=7,
        solver_run_number=2,
        initial_floor_plan=plans[0],
        refined_floor_plan=plans[1],
        post_processed_floor_plan=plans[2],
        final_floor_plan=plans[3],
    )

    pipeline_module._render_solver_attempt(
        request_id="request-42",
        attempt=attempt,
        last_refinement_profile_name="refinement_b",
        run_timestamp="20260722T061530123456Z",
    )

    stages = captured["payload"].stages
    assert tuple(stage.stage_name for stage in stages) == (
        "Initial Generation",
        "Last Refined Generation",
        "Final Floor Plan",
    )
    assert tuple(stage.floor_plan for stage in stages) == (
        plans[0],
        plans[1],
        plans[3],
    )

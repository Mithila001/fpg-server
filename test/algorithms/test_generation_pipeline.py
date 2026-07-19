from __future__ import annotations

from types import SimpleNamespace

from app.algorithms.floor_plan_post_processing import PipelineStatus
from app.algorithms.types_new import (
    FloorPlan,
    FloorPlanGenerationSpec,
    FloorPlanRoom,
    FloorSpec,
    Point,
    Polygon,
    RoomId,
    RoomSizeSpec,
    RoomSpec,
    RoomType,
)
from app.pipeline.generation import (
    GenerationPipelineRequest,
    RequestedGenerationRoom,
    run_generation_pipeline,
)


def _specification() -> FloorPlanGenerationSpec:
    size = RoomSizeSpec(2, 5, 2, 5, 4, 25)
    return FloorPlanGenerationSpec(
        FloorSpec(20, 10),
        (RoomSpec(RoomId("bedroom_1"), RoomType.BEDROOM, "Bedroom", size),),
        (),
    )


def _floor_plan() -> FloorPlan:
    return FloorPlan(
        boundary=Polygon(
            (Point(0, 0), Point(20, 0), Point(20, 10), Point(0, 10))
        ),
        rooms=[
            FloorPlanRoom(
                RoomId("bedroom_1"),
                RoomType.BEDROOM,
                "Bedroom",
                Polygon((Point(0, 0), Point(5, 0), Point(5, 5), Point(0, 5))),
            )
        ],
    )


def test_pipeline_calls_public_stages_in_order_and_uses_prepared_bounds(
    monkeypatch, capsys
):
    import app.pipeline.generation.pipeline as pipeline

    calls: list[str] = []
    captured_search_input = None
    specification = _specification()
    floor_plan = _floor_plan()

    monkeypatch.setattr(pipeline, "load_generation_reference_data", lambda: object())

    def preprocess(_value):
        calls.append("preprocessing")
        return SimpleNamespace(generation_spec=specification)

    monkeypatch.setattr(pipeline, "prepare_generation_input", preprocess)
    monkeypatch.setattr(pipeline, "create_candidate_scoring_registry", object)
    monkeypatch.setattr(pipeline, "create_candidate_scoring_config", object)

    def candidate_score(_value, **_kwargs):
        calls.append("candidate_scoring")
        return SimpleNamespace(total_score=82.0)

    monkeypatch.setattr(pipeline, "evaluate_candidate", candidate_score)

    def search(search_input):
        nonlocal captured_search_input
        calls.append("candidate_search")
        captured_search_input = search_input
        score = search_input.evaluator(
            (SimpleNamespace(room_id=RoomId("bedroom_1"), x=2.0, y=3.0),)
        )
        return SimpleNamespace(
            points=(SimpleNamespace(room_id=RoomId("bedroom_1"), x=2.0, y=3.0),),
            score=score,
            completed_trials=20,
        )

    monkeypatch.setattr(pipeline, "search_candidates", search)

    def solve(_request):
        calls.append("solver")
        return SimpleNamespace(
            solved=True,
            floor_plan=floor_plan,
            status=SimpleNamespace(value="feasible"),
        )

    monkeypatch.setattr(pipeline, "generate_floor_plan", solve)

    def post_process(_request):
        calls.append("post_processing")
        return SimpleNamespace(
            status=PipelineStatus.SUCCESS,
            floor_plan=floor_plan,
            failure=None,
        )

    monkeypatch.setattr(pipeline, "post_process_floor_plan", post_process)

    def openings(_request):
        calls.append("openings")
        return SimpleNamespace(solved=True, floor_plan=floor_plan)

    monkeypatch.setattr(pipeline, "generate_openings", openings)

    final_score = SimpleNamespace(total_score=91.0, passed_critical=True)

    def score(_floor_plan_value, _specification_value):
        calls.append("scoring")
        return final_score

    monkeypatch.setattr(pipeline, "score_floor_plan", score)

    result = run_generation_pipeline(
        GenerationPipelineRequest(
            request_id="request-1",
            max_width=100,
            max_height=80,
            aspect_ratio=1.0,
            rooms=(RequestedGenerationRoom(RoomType.BEDROOM, "bedroom_1"),),
        )
    )

    assert calls == [
        "preprocessing",
        "candidate_search",
        "candidate_scoring",
        "solver",
        "post_processing",
        "openings",
        "scoring",
    ]
    assert captured_search_input.settings.max_x == 20
    assert captured_search_input.settings.max_y == 10
    assert captured_search_input.settings.grid_resolution == 1.0
    assert captured_search_input.settings.trial_count == 20
    assert captured_search_input.settings.random_seed is None
    assert result.floor_plan is floor_plan
    assert result.scoring is final_score
    output = capsys.readouterr().out
    assert "candidate_search started" in output
    assert "candidate_search completed" in output
    assert "candidate_scoring started" not in output

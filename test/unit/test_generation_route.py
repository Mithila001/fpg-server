from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.pipeline.generation import GenerationPipelineError, GenerationStage
from app.routes.generation import router


VALID_BODY = {
    "floor_limits": {"max_width": 120, "max_height": 100},
    "aspect_ratio": "4:3",
    "rooms": [
        {"id": "bedroom_1", "room_type": "bedroom"},
        {"id": "bathroom_1", "room_type": "bathroom"},
        {"id": "kitchen_1", "room_type": "kitchen"},
        {"id": "veranda_1", "room_type": "veranda"},
    ],
}


def _client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_generation_route_returns_only_plan_and_scoring(monkeypatch):
    monkeypatch.setattr(
        "app.routes.generation.execute_generation",
        lambda _request: SimpleNamespace(
            floor_plan={"rooms": [], "openings": []},
            scoring={"total_score": 75.0},
        ),
    )

    response = _client().post("/generation", json=VALID_BODY)

    assert response.status_code == 200
    assert set(response.json()) == {"floor_plan", "scoring"}


def test_generation_route_maps_known_pipeline_error(monkeypatch):
    def fail(_request):
        raise GenerationPipelineError(
            GenerationStage.SOLVER,
            "solver_infeasible",
            "No feasible plan was found.",
            {"raw_status": "INFEASIBLE"},
        )

    monkeypatch.setattr("app.routes.generation.execute_generation", fail)

    response = _client().post("/generation", json=VALID_BODY)

    assert response.status_code == 422
    assert response.json() == {
        "stage": "solver",
        "code": "solver_infeasible",
        "message": "No feasible plan was found.",
        "details": {"raw_status": "INFEASIBLE"},
    }


def test_generation_route_keeps_fastapi_validation_errors():
    invalid = {**VALID_BODY, "floor_limits": {"max_width": 0, "max_height": 100}}

    response = _client().post("/generation", json=invalid)

    assert response.status_code == 422
    assert "detail" in response.json()


def test_generation_route_sanitizes_unexpected_errors(monkeypatch):
    def fail(_request):
        raise RuntimeError("sensitive implementation detail")

    monkeypatch.setattr("app.routes.generation.execute_generation", fail)

    response = _client().post("/generation", json=VALID_BODY)

    assert response.status_code == 500
    assert response.json() == {"message": "Generation failed unexpectedly."}

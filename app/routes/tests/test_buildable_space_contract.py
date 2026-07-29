from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def _payload() -> dict[str, object]:
    return {
        "land_boundary": {
            "points": [
                {"x": 0, "y": 0},
                {"x": 200, "y": 0},
                {"x": 200, "y": 200},
                {"x": 0, "y": 200},
            ]
        },
        "roads": [
            {
                "boundary_edge_index": 0,
                "role": "main_entry",
                "road_type": "main_road",
            }
        ],
    }


def test_success_response_has_one_flow_identity(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("OUTPUT_ROOT", str(tmp_path))
    with TestClient(app) as client:
        response = client.post("/buildable-space", json=_payload())

    assert response.status_code == 200
    body = response.json()
    assert response.headers["X-Flow-ID"] == body["flow_id"]
    assert body["units"]["project_units_per_meter"] == 10
    assert body["reference_profile"] == "mock_residential_v1"
    assert body["usable_land"]["area"] == (
        body["usable_land"]["width"] * body["usable_land"]["length"]
    )


def test_structural_and_business_errors_have_flow_identity(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("OUTPUT_ROOT", str(tmp_path))
    with TestClient(app) as client:
        structural = client.post(
            "/buildable-space",
            json={"land_boundary": {"points": []}},
        )
        payload = _payload()
        payload["land_boundary"] = {
            "points": [
                {"x": 0, "y": 0},
                {"x": 100, "y": 0},
                {"x": 200, "y": 0},
                {"x": 200, "y": 200},
                {"x": 0, "y": 200},
            ]
        }
        business = client.post("/buildable-space", json=payload)

    for response in (structural, business):
        assert response.status_code == 422
        assert response.headers["X-Flow-ID"]
    assert structural.json()["error"]["code"] == "invalid_request"
    assert business.json()["error"]["code"] == "invalid_land_boundary"


def test_float_boolean_and_extra_coordinates_are_rejected(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("OUTPUT_ROOT", str(tmp_path))
    payload = _payload()
    payload["land_boundary"] = {
        "points": [
            {"x": False, "y": 0},
            {"x": 200.0, "y": 0},
            {"x": 200, "y": 200, "z": 1},
            {"x": 0, "y": 200},
        ]
    }
    with TestClient(app) as client:
        response = client.post("/buildable-space", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core_config import CoreConfigLoadError
from app.main import app


def _valid_rooms() -> list[dict[str, str]]:
    return [
        {"room_type": "bedroom"},
        {"room_type": "bathroom"},
        {"room_type": "living_room"},
        {"room_type": "kitchen"},
        {"room_type": "dining_room"},
        {"room_type": "veranda"},
    ]


def test_metadata_is_the_single_generation_discovery_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/metadata")
        removed = client.get("/generation/room-size-constraints")

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == 1
    assert [item["value"] for item in body["road_types"]] == [
        "main_road",
        "private_road",
    ]
    assert [item["name"] for item in body["road_types"]] == [
        "MAIN_ROAD",
        "PRIVATE_ROAD",
    ]
    assert [item["label"] for item in body["compatible_aspect_ratios"]] == [
        "1:2",
        "3:4",
        "1:1",
        "4:3",
        "2:1",
    ]
    assert body["buffers"] == {
        "hallway_area": 300.0,
        "floor_area": 500.0,
        "unit": "square_project_units",
    }
    hallway = next(
        item for item in body["room_requirements"] if item["room_type"] == "hallway"
    )
    assert hallway == {
        "room_type": "hallway",
        "name": "HALLWAY",
        "min_count": 1,
        "max_count": 1,
        "client_selectable": False,
    }
    assert all(
        item["room_type"] != "open_area"
        for item in body["generation_reference_data"]["room_sizes"]
    )
    assert removed.status_code == 404
    assert removed.json()["error"]["code"] == "not_found"


def test_generation_request_rejects_removed_required_field() -> None:
    rooms = _valid_rooms()
    rooms[0]["required"] = "true"
    with TestClient(app) as client:
        response = client.post(
            "/generation",
            json={
                "floor_limits": {"max_width": 120, "max_length": 100},
                "aspect_ratio": "1:1",
                "rooms": rooms,
            },
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert response.json()["error"]["stage"] == "request_validation"


def test_metadata_reference_failure_uses_common_error_envelope(
    monkeypatch,
) -> None:
    def fail_reference_load(_app):
        raise CoreConfigLoadError("invalid test reference")

    monkeypatch.setattr(
        "app.routes.generation.get_fpg_core_config",
        fail_reference_load,
    )
    with TestClient(app) as client:
        response = client.get("/metadata")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "reference_data_unavailable",
            "message": "Server metadata is currently unavailable.",
            "stage": "metadata",
            "details": {},
        }
    }


def test_preprocessing_and_not_found_errors_share_envelope(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("OUTPUT_ROOT", str(tmp_path))
    with TestClient(app) as client:
        invalid_generation = client.post(
            "/generation",
            json={
                "floor_limits": {"max_width": 120, "max_length": 100},
                "aspect_ratio": "1:1",
                "rooms": _valid_rooms()[:-1],
            },
        )
        missing_job = client.delete("/generation/stream/not-a-job")

    assert invalid_generation.status_code == 422
    assert invalid_generation.json()["error"]["code"] == "invalid_room_count"
    assert invalid_generation.json()["error"]["details"]["preprocessing_stage"] == (
        "input_validation"
    )
    assert missing_job.status_code == 404
    assert missing_job.json() == {
        "error": {
            "code": "not_found",
            "message": "No active streamed generation job was found.",
            "stage": "cancellation",
            "details": {"job_id": "not-a-job"},
        }
    }

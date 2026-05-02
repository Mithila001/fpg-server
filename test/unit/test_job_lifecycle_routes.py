from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.buildable_space_route import router as buildable_router
from app.routes.routes import router as algorithms_router


class _StubRegistry:
    def __init__(self):
        self.submit_response = {
            "accepted": True,
            "job_id": "job-1",
            "status": "SEARCHING",
            "message": "Job accepted for processing.",
        }
        self.cancel_response = {
            "cancelled": True,
            "message": "Job cancelled successfully.",
            "job": {
                "job_id": "job-1",
                "job_kind": "FORMAT_V2",
                "client_key": "cli-1",
                "pid": 42,
                "status": "TERMINATED",
                "created_at": "now",
                "updated_at": "now",
                "events": [],
                "result": None,
            },
        }
        self.job_response = {
            "job_id": "job-1",
            "job_kind": "FORMAT_V2",
            "client_key": "cli-1",
            "pid": 42,
            "status": "COMPLETED",
            "created_at": "now",
            "updated_at": "now",
            "events": [
                {
                    "id": 1,
                    "timestamp": "now",
                    "event": "JOB_STARTED",
                    "message": "Job accepted and running.",
                    "data": {"status": "SEARCHING"},
                },
                {
                    "id": 2,
                    "timestamp": "now",
                    "event": "trial_completed",
                    "message": "trial 1 complete",
                    "data": {"trial_number": 1},
                },
                {
                    "id": 3,
                    "timestamp": "now",
                    "event": "COMPLETED",
                    "message": "Job finished processing.",
                    "data": {"status": "COMPLETED"},
                },
            ],
            "result": {"status": "OK", "message": "done"},
        }
        self.active_response = self.job_response

    def submit_job(self, **_kwargs):
        return self.submit_response

    def cancel_job(self, **_kwargs):
        self.active_response = self.cancel_response["job"]
        return self.cancel_response

    def get_job(self, _job_id):
        return self.job_response

    def get_active_job_for_client(self, _client_key):
        return self.active_response

    def get_job_events_since(self, _job_id, after_event_id=0):
        return [
            event
            for event in self.job_response["events"]
            if event["id"] > after_event_id
        ]

    def wait_for_job_events(self, _job_id, _after_event_id=0, timeout=1.0):
        return []


def _client_with_stub_registry(monkeypatch):
    app = FastAPI()
    app.include_router(algorithms_router)
    app.include_router(buildable_router)
    stub = _StubRegistry()
    monkeypatch.setattr("app.routes.routes.job_registry", stub)
    monkeypatch.setattr("app.routes.buildable_space_route.job_registry", stub)
    return TestClient(app), stub


def test_submit_endpoints_and_lockout(monkeypatch):
    client, stub = _client_with_stub_registry(monkeypatch)
    format_payload = {
        "floor_width": 1200,
        "floor_height": 1000,
        "room_template": {
            "name": "basic-template",
            "data": [],
        },
    }
    response = client.post(
        "/algorithms/format/v2", json=format_payload, headers={"X-Client-Id": "cli-1"}
    )
    assert response.status_code == 202
    assert response.json()["job_id"] == "job-1"

    buildable_payload = {
        "area": 1500000,
        "segmentsCoordinates": [
            {"x": 0, "y": 0},
            {"x": 1000, "y": 0},
            {"x": 1000, "y": 1000},
        ],
        "roadConnected": [],
    }
    response = client.post(
        "/algorithms/buildable-space",
        json=buildable_payload,
        headers={"X-Client-Id": "cli-1"},
    )
    assert response.status_code == 202

    stub.submit_response = {
        "accepted": False,
        "message": "Process is Already Running",
        "job_id": "job-1",
    }
    lockout = client.post(
        "/algorithms/format/v2", json=format_payload, headers={"X-Client-Id": "cli-1"}
    )
    assert lockout.status_code == 409


def test_cancel_and_status_endpoints(monkeypatch):
    client, _stub = _client_with_stub_registry(monkeypatch)
    cancel = client.post(
        "/algorithms/cancel", json={"job_id": "job-1"}, headers={"X-Client-Id": "cli-1"}
    )
    assert cancel.status_code == 200
    assert cancel.json()["cancelled"] is True

    job = client.get("/algorithms/job/job-1")
    assert job.status_code == 200
    assert job.json()["job_id"] == "job-1"

    active = client.get("/algorithms/job/active", headers={"X-Client-Id": "cli-1"})
    assert active.status_code == 200
    assert active.json()["status"] == "TERMINATED"


def test_job_events_stream(monkeypatch):
    client, _stub = _client_with_stub_registry(monkeypatch)
    response = client.get("/algorithms/job/job-1/events")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "trial_completed" in response.text
    assert "COMPLETED" in response.text

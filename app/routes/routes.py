from __future__ import annotations

from typing import Any
import json

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from app.services.job_lifecycle import JobKind, JobStatus, job_registry
from app.schemas.db.room_setup_template import RoomSetupTemplateBase


class JobSubmitResponse(BaseModel):
    job_id: str
    status: str
    message: str


class FormatterV2ApiRequest(BaseModel):
    floor_width: float
    floor_height: float
    aspect_ratio: float
    room_template: RoomSetupTemplateBase
    should_optuna_run: bool = False
    optuna_trial_count: int = 20

    @field_validator("aspect_ratio", mode="before")
    def _validate_and_normalize_aspect_ratio(cls, v):
        """Normalize aspect_ratio input to a float H/W and validate range [0.5,2.0].

        Accepts numeric values or string forms like "2:1" interpreted as H:W.
        """
        # Accept numeric values
        if isinstance(v, (int, float)):
            ratio = float(v)
        elif isinstance(v, str):
            parts = v.split(":")
            if len(parts) != 2:
                raise ValueError(
                    "Invalid aspect_ratio format. Use numeric or 'H:W' string like '2:1'."
                )
            try:
                h = float(parts[0])
                w = float(parts[1])
            except Exception:
                raise ValueError("Invalid numeric parts in aspect_ratio string.")
            if w == 0:
                raise ValueError("Invalid aspect_ratio: width part cannot be zero.")
            ratio = h / w
        else:
            raise ValueError("aspect_ratio must be a number or a string of the form 'H:W'.")

        if not (0.5 <= ratio <= 2.0):
            raise ValueError("aspect_ratio must be between 0.5 and 2.0 (H/W).")
        return ratio


router = APIRouter(prefix="/algorithms", tags=["algorithms"])


class CancelJobRequest(BaseModel):
    job_id: str | None = None


class JobStateResponse(BaseModel):
    job_id: str
    job_kind: str
    client_key: str
    pid: int
    status: str
    created_at: str
    updated_at: str
    events: list[dict[str, Any]]
    result: dict[str, Any] | None = None


class CancelJobResponse(BaseModel):
    cancelled: bool
    message: str
    job: JobStateResponse | None = None


def _resolve_client_key(request: Request, x_client_id: str | None) -> str:
    if x_client_id and x_client_id.strip():
        return x_client_id.strip()
    return request.client.host if request.client else "unknown"


@router.post("/format/v2", response_model=JobSubmitResponse, status_code=202)
def submit_formatted_layout_v2(
    request: Request,
    body: FormatterV2ApiRequest,
    x_client_id: str | None = Header(default=None),
):
    client_key = _resolve_client_key(request, x_client_id)
    submission = job_registry.submit_job(
        job_kind=JobKind.FORMAT_V2,
        client_key=client_key,
        request_payload=body.model_dump(),
    )
    if not submission["accepted"]:
        raise HTTPException(
            status_code=409,
            detail=submission["message"],
        )
    return JobSubmitResponse(**submission)


@router.post("/cancel", response_model=CancelJobResponse)
def cancel_job(
    request: Request,
    body: CancelJobRequest,
    x_client_id: str | None = Header(default=None),
):
    client_key = _resolve_client_key(request, x_client_id)
    response = job_registry.cancel_job(client_key=client_key, job_id=body.job_id)
    job_payload = response.get("job")
    if response["cancelled"]:
        return CancelJobResponse(
            cancelled=True,
            message=response["message"],
            job=JobStateResponse(**job_payload) if job_payload else None,
        )
    if body.job_id:
        raise HTTPException(
            status_code=404,
            detail=response["message"],
        )
    raise HTTPException(status_code=409, detail=response["message"])


@router.get("/job/active", response_model=JobStateResponse)
def get_active_job(
    request: Request,
    x_client_id: str | None = Header(default=None),
):
    client_key = _resolve_client_key(request, x_client_id)
    payload = job_registry.get_active_job_for_client(client_key)
    if payload is None:
        raise HTTPException(status_code=404, detail="No active job found.")
    return JobStateResponse(**payload)


def _format_sse_event(event: dict[str, Any]) -> str:
    parts = [f"id: {event.get('id', 0)}", f"event: {event.get('event', 'message')}"]
    data_payload = {
        "id": event.get("id"),
        "event": event.get("event"),
        "message": event.get("message"),
        "timestamp": event.get("timestamp"),
        "data": event.get("data", {}),
    }
    parts.append(f"data: {json.dumps(data_payload, ensure_ascii=False, default=str)}")
    return "\n".join(parts) + "\n\n"


@router.get("/job/{job_id}/events")
def stream_job_events(
    job_id: str,
    last_event_id: int | None = None,
    x_client_id: str | None = Header(default=None),
    last_event_id_header: str | None = Header(default=None, alias="Last-Event-ID"),
):
    def _parse_last_event_id() -> int:
        for value in (last_event_id_header, last_event_id):
            if value is None:
                continue
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
        return 0

    def event_stream():
        current_last_id = _parse_last_event_id()
        initial_events = job_registry.get_job_events_since(job_id, current_last_id)
        for event in initial_events:
            current_last_id = int(event.get("id", current_last_id))
            yield _format_sse_event(event)

        while True:
            payload = job_registry.get_job(job_id)
            if payload is None:
                yield 'event: job_missing\ndata: {"message": "Job not found."}\n\n'
                return

            for event in job_registry.wait_for_job_events(
                job_id, current_last_id, timeout=10.0
            ):
                current_last_id = int(event.get("id", current_last_id))
                yield _format_sse_event(event)

            payload = job_registry.get_job(job_id)
            if payload is None:
                yield 'event: job_missing\ndata: {"message": "Job not found."}\n\n'
                return

            if payload["status"] != JobStatus.SEARCHING.value:
                return

            yield ": keepalive\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/job/{job_id}", response_model=JobStateResponse)
def get_job_status(job_id: str):
    payload = job_registry.get_job(job_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return JobStateResponse(**payload)

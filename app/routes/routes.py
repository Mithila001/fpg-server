from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from app.services.job_lifecycle import JobKind, job_registry
from app.schemas.db.room_setup_template import RoomSetupTemplateBase


class JobSubmitResponse(BaseModel):
    job_id: str
    status: str
    message: str


class FormatterV2ApiRequest(BaseModel):
    floor_width: float
    floor_height: float
    room_template: RoomSetupTemplateBase
    should_optuna_run: bool = False
    optuna_trial_count: int = 20


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


@router.get("/job/{job_id}", response_model=JobStateResponse)
def get_job_status(job_id: str):
    payload = job_registry.get_job(job_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return JobStateResponse(**payload)

from __future__ import annotations

from enum import StrEnum
from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException


class ApiErrorCode(StrEnum):
    INVALID_REQUEST = "invalid_request"
    NOT_FOUND = "not_found"
    REFERENCE_DATA_UNAVAILABLE = "reference_data_unavailable"
    UNEXPECTED_ERROR = "unexpected_error"


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    stage: str
    details: dict[str, Any] = Field(default_factory=dict)


class ApiErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ApiError


def api_error_response(
    status_code: int,
    code: str,
    message: str,
    stage: str,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = ApiErrorResponse(
        error=ApiError(
            code=code,
            message=message,
            stage=stage,
            details=details or {},
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(body),
        headers=headers,
    )


async def api_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = [
        {
            "location": [str(part) for part in error.get("loc", ())],
            "code": str(error.get("type", "validation_error")),
            "message": str(error.get("msg", "Invalid value.")),
        }
        for error in exc.errors()
    ]
    headers: dict[str, str] = {}
    context = getattr(request.state, "buildable_space_execution_context", None)
    flow_id = getattr(context, "flow_id", None)
    if flow_id is not None:
        headers["X-Flow-ID"] = str(flow_id)
    return api_error_response(
        status_code=422,
        code=ApiErrorCode.INVALID_REQUEST.value,
        message="The request is invalid.",
        stage="request_validation",
        details={"errors": errors},
        headers=headers or None,
    )


async def api_http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    code = (
        ApiErrorCode.NOT_FOUND.value
        if exc.status_code == 404
        else ApiErrorCode.INVALID_REQUEST.value
    )
    message = (
        "The requested resource was not found."
        if exc.status_code == 404
        else str(exc.detail)
    )
    return api_error_response(
        status_code=exc.status_code,
        code=code,
        message=message,
        stage="routing",
        details={"path": request.url.path},
        headers=dict(exc.headers or {}),
    )


async def api_unexpected_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return api_error_response(
        status_code=500,
        code=ApiErrorCode.UNEXPECTED_ERROR.value,
        message="The server failed to process the request unexpectedly.",
        stage="response",
        details={},
    )

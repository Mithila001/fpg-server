from __future__ import annotations

import json
from typing import Any

from fastapi import Request

from app.util.logger.log_manager import LogManager


class ApiLogger:
    """Use-case logger for API request/response activity."""

    USE_CASE = "api"
    MAX_TEXT_BYTES = 10_000

    @staticmethod
    def _decode_body(body: bytes) -> Any:
        if not body:
            return None

        trimmed = body[: ApiLogger.MAX_TEXT_BYTES]
        text = trimmed.decode("utf-8", errors="replace")

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    @staticmethod
    def _headers_subset(request: Request) -> dict[str, str]:
        headers_to_capture = {
            "content-type",
            "content-length",
            "user-agent",
            "x-forwarded-for",
        }
        return {
            key: value
            for key, value in request.headers.items()
            if key.lower() in headers_to_capture
        }

    @staticmethod
    def request_response(
        request: Request,
        request_body: bytes,
        response_body: bytes,
        status_code: int,
        duration_ms: float,
        error: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "request": {
                "method": request.method,
                "path": request.url.path,
                "query": dict(request.query_params),
                "client_ip": request.client.host if request.client else None,
                "headers": ApiLogger._headers_subset(request),
                "data": ApiLogger._decode_body(request_body),
            },
            "response": {
                "status_code": int(status_code),
                "data": ApiLogger._decode_body(response_body),
            },
            "duration_ms": round(float(duration_ms), 2),
        }

        if error is not None:
            payload["error"] = error

        LogManager.log_event(
            use_case=ApiLogger.USE_CASE,
            event="api_request_response",
            payload=payload,
            message=f"{request.method} {request.url.path}",
        )

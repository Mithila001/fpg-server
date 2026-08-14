from __future__ import annotations

import json
import traceback
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qsl

from app.core_config import ServerConfig

AsgiMessage = dict[str, Any]
AsgiReceive = Callable[[], Awaitable[AsgiMessage]]
AsgiSend = Callable[[AsgiMessage], Awaitable[None]]
AsgiApp = Callable[[dict[str, Any], AsgiReceive, AsgiSend], Awaitable[None]]

_lock = Lock()
_sensitive_fragments = ("authorization", "cookie", "token", "secret", "password", "api_key")


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): (
                "[REDACTED]"
                if any(fragment in str(key).lower() for fragment in _sensitive_fragments)
                else _redact(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _decode_body(body: bytes) -> Any:
    if not body:
        return None
    try:
        return _redact(json.loads(body.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"non_json_bytes": len(body)}


class JsonlLogWriter:
    def __init__(self, output_root: Path) -> None:
        self.root = output_root.resolve() / "logs"

    def api(self, record: dict[str, Any]) -> None:
        self._append("api", record)

    def error(self, record: dict[str, Any]) -> None:
        self._append("errors", record)

    def exception(
        self,
        *,
        stage: str,
        code: str,
        exception: BaseException,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.error(
            {
                "timestamp_utc": datetime.now(UTC).isoformat(),
                "stage": stage,
                "code": code,
                "recoverable": False,
                "exception_type": type(exception).__name__,
                "message": str(exception),
                "traceback": "".join(
                    traceback.format_exception(type(exception), exception, exception.__traceback__)
                ),
                "details": _redact(details or {}),
            }
        )

    def _append(self, category: str, record: dict[str, Any]) -> None:
        now = datetime.now(UTC)
        path = self.root / category / f"{now:%Y-%m-%d}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(_redact(record), ensure_ascii=False, separators=(",", ":"))
        with _lock:
            with path.open("a", encoding="utf-8") as stream:
                stream.write(line + "\n")
                stream.flush()


class ApiLoggingMiddleware:
    def __init__(self, app: AsgiApp, config: ServerConfig) -> None:
        self.app = app
        self.writer = JsonlLogWriter(config.server.output_root)

    async def __call__(
        self, scope: dict[str, Any], receive: AsgiReceive, send: AsgiSend
    ) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        started = perf_counter()
        request_body = bytearray()
        response_body = bytearray()
        status_code = 500
        streaming = False

        async def logged_receive() -> AsgiMessage:
            message = await receive()
            if message.get("type") == "http.request":
                request_body.extend(message.get("body", b""))
            return message

        async def logged_send(message: AsgiMessage) -> None:
            nonlocal status_code, streaming
            if message.get("type") == "http.response.start":
                status_code = int(message.get("status", 500))
                headers = {
                    bytes(key).lower(): bytes(value)
                    for key, value in message.get("headers", [])
                }
                streaming = b"text/event-stream" in headers.get(b"content-type", b"")
            elif message.get("type") == "http.response.body" and not streaming:
                response_body.extend(message.get("body", b""))
            await send(message)

        try:
            await self.app(scope, logged_receive, logged_send)
        except BaseException as exc:
            self.writer.exception(
                stage="api",
                code="unhandled_api_exception",
                exception=exc,
                details={"method": scope.get("method"), "path": scope.get("path")},
            )
            raise
        finally:
            raw_headers = {
                bytes(key).decode("latin-1").lower(): bytes(value).decode("latin-1")
                for key, value in scope.get("headers", [])
            }
            safe_headers = {
                key: raw_headers[key]
                for key in ("accept", "content-type", "origin", "user-agent", "x-request-id")
                if key in raw_headers
            }
            client = scope.get("client")
            record = {
                "timestamp_utc": datetime.now(UTC).isoformat(),
                "method": scope.get("method"),
                "path": scope.get("path"),
                "query": _redact(
                    dict(
                        parse_qsl(
                            bytes(scope.get("query_string", b"")).decode("latin-1"),
                            keep_blank_values=True,
                        )
                    )
                ),
                "status_code": status_code,
                "duration_ms": (perf_counter() - started) * 1000,
                "client": client[0] if isinstance(client, tuple) and client else None,
                "headers": safe_headers,
                "request_body": _decode_body(bytes(request_body)),
                "response_body": None if streaming else _decode_body(bytes(response_body)),
                "streaming": streaming,
            }
            self.writer.api(record)
            if status_code >= 400:
                self.writer.error(
                    {
                        "timestamp_utc": record["timestamp_utc"],
                        "stage": "api",
                        "code": "api_error_response",
                        "recoverable": False,
                        "method": record["method"],
                        "path": record["path"],
                        "status_code": status_code,
                        "response_body": record["response_body"],
                    }
                )


__all__ = ["ApiLoggingMiddleware", "JsonlLogWriter"]

from __future__ import annotations

import json
import os
import sys
from itertools import count
from threading import Lock
from typing import Any

from app.artifacts import (
    ArtifactFormat,
    ArtifactKind,
    ArtifactReference,
    ArtifactScope,
    ArtifactStorage,
    ArtifactWriteRequest,
    FeatureKey,
    WriteMode,
)
from app.artifacts.serializers import to_json_value
from app.core.execution import ExecutionContext, normalize_slug

from .enums import LogLevel
from .models import ExceptionData, LogRecord

_event_counter = count(1)
_event_counter_lock = Lock()


class BaseLogger:
    """Validate common records and persist each event as one atomic JSON file."""

    def __init__(
        self,
        storage: ArtifactStorage | None = None,
        *,
        minimum_level: LogLevel | None = None,
        console: bool = True,
    ) -> None:
        self.storage = storage or ArtifactStorage()
        configured = os.getenv("LOG_LEVEL", "INFO").strip().upper()
        try:
            self.minimum_level = minimum_level or LogLevel(configured)
        except ValueError:
            self.minimum_level = minimum_level or LogLevel.INFO
        self.console = console

    def log(
        self,
        *,
        feature: FeatureKey,
        event: str,
        level: LogLevel = LogLevel.INFO,
        message: str | None = None,
        context: ExecutionContext | None = None,
        payload: dict[str, Any] | None = None,
        exception: BaseException | None = None,
    ) -> ArtifactReference | None:
        if level.priority < self.minimum_level.priority:
            return None
        try:
            safe_payload = to_json_value(payload or {})
            if not isinstance(safe_payload, dict):
                raise TypeError("log payload must serialize to an object")
            record = LogRecord(
                level=level,
                feature=feature,
                event=normalize_slug(event),
                message=message or event.replace("_", " "),
                execution_context=context,
                payload=safe_payload,
                exception=(
                    ExceptionData(type(exception).__name__, str(exception))
                    if exception is not None
                    else None
                ),
            )
            serialized = record.to_dict()
            if self.console:
                print(
                    json.dumps(
                        serialized,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                    file=sys.stdout,
                    flush=True,
                )
            timestamp = record.timestamp_utc
            with _event_counter_lock:
                sequence = next(_event_counter)
            semantic_name = (
                f"{timestamp:%Y%m%dT%H%M%S.%fZ}_"
                f"p{os.getpid()}_c{sequence:06d}_{record.event}"
            )
            return self.storage.save_json(
                ArtifactWriteRequest(
                    feature=feature,
                    artifact_kind=ArtifactKind.EVENT_LOG,
                    artifact_format=ArtifactFormat.JSON,
                    artifact_scope=(
                        ArtifactScope.FLOW
                        if context is not None
                        else ArtifactScope.GLOBAL
                    ),
                    semantic_name=semantic_name,
                    execution_context=context,
                    write_mode=WriteMode.CREATE,
                    metadata={"event_date": f"{timestamp:%Y-%m-%d}"},
                ),
                serialized,
            )
        except Exception as logging_error:
            print(
                json.dumps(
                    {
                        "level": "ERROR",
                        "feature": "application",
                        "event": "logging_failure",
                        "message": str(logging_error),
                    },
                    separators=(",", ":"),
                ),
                file=sys.stderr,
                flush=True,
            )
            return None

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Mapping

from app.artifacts import FeatureKey
from app.artifacts.models import JsonValue
from app.core.execution import ExecutionContext

from .enums import LogLevel


@dataclass(frozen=True, slots=True)
class ExceptionData:
    type: str
    message: str


@dataclass(frozen=True, slots=True)
class LogRecord:
    level: LogLevel
    feature: FeatureKey
    event: str
    message: str
    execution_context: ExecutionContext | None = None
    payload: Mapping[str, JsonValue] = field(default_factory=dict)
    exception: ExceptionData | None = None
    schema_version: str = "1.0"
    timestamp_utc: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, JsonValue]:
        result: dict[str, JsonValue] = {
            "schema_version": self.schema_version,
            "timestamp_utc": self.timestamp_utc.isoformat(),
            "level": self.level.value,
            "feature": self.feature.value,
            "event": self.event,
            "message": self.message,
            "execution_context": (
                self.execution_context.to_dict()
                if self.execution_context is not None
                else None
            ),
            "payload": dict(self.payload),
        }
        if self.exception is not None:
            result["exception"] = {
                "type": self.exception.type,
                "message": self.exception.message,
            }
        return result

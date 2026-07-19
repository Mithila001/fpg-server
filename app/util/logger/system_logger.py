from __future__ import annotations

import json
import logging
import os
import sys
from datetime import UTC, datetime
from threading import Lock
from typing import Any, ClassVar


_VALID_LEVELS: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


class _StructuredEventFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "tag": getattr(record, "event_tag", "application"),
            "event": getattr(record, "event_name", record.getMessage()),
            "data": getattr(record, "event_data", {}),
        }
        return json.dumps(
            payload,
            ensure_ascii=False,
            default=str,
            separators=(",", ":"),
        )


class SystemLogger:
    """Write pipeline events as structured JSON lines to standard output."""

    _logger: ClassVar[logging.Logger | None] = None
    _lock: ClassVar[Lock] = Lock()

    @classmethod
    def _get_logger(cls) -> logging.Logger:
        if cls._logger is not None:
            return cls._logger

        with cls._lock:
            if cls._logger is not None:
                return cls._logger

            logger = logging.getLogger("fpg.pipeline")
            logger.handlers.clear()
            logger.propagate = False

            configured_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
            logger.setLevel(_VALID_LEVELS.get(configured_level, logging.INFO))

            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(_StructuredEventFormatter())
            logger.addHandler(handler)

            cls._logger = logger
            return logger

    @classmethod
    def log_event(
        cls,
        tag: str,
        event: str,
        level: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        normalized_level = str(level).strip().upper()
        if normalized_level not in _VALID_LEVELS:
            raise ValueError(
                "level must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL"
            )

        cls._get_logger().log(
            _VALID_LEVELS[normalized_level],
            event,
            extra={
                "event_tag": str(tag),
                "event_name": str(event),
                "event_data": dict(data or {}),
            },
        )


log_event = SystemLogger.log_event

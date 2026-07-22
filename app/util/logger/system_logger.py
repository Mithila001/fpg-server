from __future__ import annotations

import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any, ClassVar

from app.util.output_paths import (
    create_artifact_path,
    create_timestamped_directory,
    get_output_root,
    utc_timestamp,
)


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
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(
            payload,
            ensure_ascii=False,
            default=str,
            separators=(",", ":"),
        )


class SystemLogger:
    """Write structured events to stdout and managed JSONL files."""

    _logger: ClassVar[logging.Logger | None] = None
    _handlers: ClassVar[tuple[logging.Handler, ...]] = ()
    _process_id: ClassVar[int | None] = None
    _log_file: ClassVar[Path | None] = None
    _lock: ClassVar[Lock] = Lock()

    @classmethod
    def _get_logger(cls) -> logging.Logger:
        process_id = os.getpid()
        if cls._logger is not None and cls._process_id == process_id:
            return cls._logger

        with cls._lock:
            if cls._logger is not None and cls._process_id == process_id:
                return cls._logger

            for handler in cls._handlers:
                handler.close()

            logger = logging.getLogger("fpg.pipeline")
            logger.handlers.clear()
            logger.propagate = False

            configured_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
            logger.setLevel(_VALID_LEVELS.get(configured_level, logging.INFO))

            formatter = _StructuredEventFormatter()
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)

            run_timestamp = utc_timestamp()
            log_directory = create_timestamped_directory(
                get_output_root() / "logs",
                f"server-{process_id}",
                run_timestamp=run_timestamp,
            )
            log_file = create_artifact_path(
                log_directory,
                f"application-{process_id}",
                "jsonl",
            )
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(formatter)

            handlers = (console_handler, file_handler)
            for handler in handlers:
                logger.addHandler(handler)

            cls._logger = logger
            cls._handlers = handlers
            cls._process_id = process_id
            cls._log_file = log_file
            cls._configure_external_loggers(handlers, logger.level)
            return logger

    @staticmethod
    def _configure_external_loggers(
        handlers: tuple[logging.Handler, ...],
        level: int,
    ) -> None:
        for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "optuna"):
            logger = logging.getLogger(logger_name)
            logger.handlers.clear()
            logger.handlers.extend(handlers)
            logger.setLevel(level)
            logger.propagate = False

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


def configure_application_logging() -> Path:
    """Initialize managed logging and return the active JSONL path."""

    SystemLogger._get_logger()
    assert SystemLogger._log_file is not None
    return SystemLogger._log_file

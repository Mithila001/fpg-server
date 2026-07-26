from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, ClassVar

from app.artifacts import ArtifactStorage, FeatureKey
from app.core.execution import ExecutionContext

from .base_logger import BaseLogger
from .enums import LogLevel


class _ExternalLogHandler(logging.Handler):
    def __init__(self, logger: BaseLogger) -> None:
        super().__init__()
        self.structured_logger = logger

    def emit(self, record: logging.LogRecord) -> None:
        level = {
            logging.DEBUG: LogLevel.DEBUG,
            logging.INFO: LogLevel.INFO,
            logging.WARNING: LogLevel.WARNING,
            logging.ERROR: LogLevel.ERROR,
            logging.CRITICAL: LogLevel.CRITICAL,
        }.get(record.levelno, LogLevel.INFO)
        self.structured_logger.log(
            feature=FeatureKey.APPLICATION,
            event=record.name.replace(".", "_"),
            level=level,
            message=record.getMessage(),
            payload={"logger": record.name},
            exception=record.exc_info[1] if record.exc_info else None,
        )


class SystemLogger:
    """Compatibility facade delegating all persistence to ``BaseLogger``."""

    _logger: ClassVar[BaseLogger | None] = None
    _handlers: ClassVar[tuple[logging.Handler, ...]] = ()
    _process_id: ClassVar[int | None] = None
    _log_file: ClassVar[Path | None] = None

    @classmethod
    def _get_logger(cls) -> BaseLogger:
        process_id = os.getpid()
        if cls._logger is None or cls._process_id != process_id:
            for handler in cls._handlers:
                handler.close()
            storage = ArtifactStorage()
            cls._logger = BaseLogger(storage)
            cls._process_id = process_id
            cls._log_file = storage.config.output_root / "application" / "json"
            cls._log_file.mkdir(parents=True, exist_ok=True)
            handler = _ExternalLogHandler(cls._logger)
            cls._handlers = (handler,)
            configured_level = getattr(
                logging,
                os.getenv("LOG_LEVEL", "INFO").strip().upper(),
                logging.INFO,
            )
            for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "optuna"):
                external = logging.getLogger(logger_name)
                external.handlers.clear()
                external.addHandler(handler)
                external.setLevel(configured_level)
                external.propagate = False
        return cls._logger

    @classmethod
    def log_event(
        cls,
        tag: str,
        event: str,
        level: str,
        data: dict[str, Any] | None = None,
        *,
        context: ExecutionContext | None = None,
        message: str | None = None,
        exception: BaseException | None = None,
    ) -> None:
        try:
            normalized_level = LogLevel(str(level).strip().upper())
        except ValueError as exc:
            raise ValueError(
                "level must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL"
            ) from exc
        try:
            feature = FeatureKey(str(tag).strip().lower())
        except ValueError:
            feature = FeatureKey.APPLICATION
        cls._get_logger().log(
            feature=feature,
            event=event,
            level=normalized_level,
            message=message,
            context=context,
            payload=data,
            exception=exception,
        )


log_event = SystemLogger.log_event


def configure_application_logging() -> Path:
    SystemLogger._get_logger()
    assert SystemLogger._log_file is not None
    return SystemLogger._log_file

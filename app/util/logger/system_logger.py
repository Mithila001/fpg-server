from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


class _JsonlFormatter(logging.Formatter):
    """Serialize log records as JSON lines with the required fields."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, timezone.utc)
        entry: dict[str, Any] = {
            "time": timestamp.isoformat(),
            "ts": f"{record.created:0.6f}",
            "level": record.levelname,
            "tag": getattr(record, "tag", ""),
            "event": getattr(record, "event", ""),
            "data": getattr(record, "data", {}),
        }
        return json.dumps(entry, ensure_ascii=True, default=str)


class SystemLogger:
    """Centralized server logger writing to logs/server_logs.jsonl."""

    _logger: logging.Logger | None = None
    _log_file_name = "server_logs.jsonl"
    _max_bytes = 2 * 1024 * 1024
    _backup_count = 5

    @staticmethod
    def _logs_dir() -> Path:
        return Path(__file__).resolve().parents[3] / "logs"

    @classmethod
    def _ensure_logger(cls) -> logging.Logger:
        if cls._logger is not None:
            return cls._logger

        logs_dir = cls._logs_dir()
        try:
            logs_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:  # noqa: BLE001
            cls._logger = logging.getLogger("app.server_logs")
            cls._logger.propagate = False
            cls._logger.setLevel(logging.DEBUG)
            cls._logger.handlers.clear()
            cls._logger.addHandler(logging.NullHandler())
            print(f"[LOGGER WARNING] cannot create logs directory at {logs_dir}: {exc}", file=sys.stderr)
            return cls._logger

        log_file_path = logs_dir / cls._log_file_name
        handler = RotatingFileHandler(
            filename=log_file_path,
            maxBytes=cls._max_bytes,
            backupCount=cls._backup_count,
            encoding="utf-8",
        )
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(_JsonlFormatter())

        cls._logger = logging.getLogger("app.server_logs")
        cls._logger.setLevel(logging.DEBUG)
        cls._logger.propagate = False
        cls._logger.handlers.clear()
        cls._logger.addHandler(handler)
        return cls._logger

    @classmethod
    def log_event(
        cls,
        tag: str,
        event: str,
        level: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Write a structured JSONL event to the centralized server log."""
        logger = cls._ensure_logger()
        normalized_level = str(level).upper().strip()

        if normalized_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError(
                "level must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL"
            )

        safe_data = data if isinstance(data, dict) else {"value": data}

        try:
            logger.log(
                getattr(logging, normalized_level),
                "",
                extra={
                    "tag": tag,
                    "event": event,
                    "data": safe_data,
                },
            )
        except Exception as exc:  # noqa: BLE001
            print(
                f"[LOGGER WARNING] failed to write event '{event}' with tag '{tag}': {exc}",
                file=sys.stderr,
            )


# Module-level convenience helper
log_event = SystemLogger.log_event

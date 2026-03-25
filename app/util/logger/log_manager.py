from __future__ import annotations

import json
import logging
import sys
import tempfile
import threading
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


class _JsonlFormatter(logging.Formatter):
    """Serialize log records as JSON lines for easy filtering and parsing."""

    def format(self, record: logging.LogRecord) -> str:
        payload = getattr(record, "payload", {})
        if not isinstance(payload, dict):
            payload = {"value": payload}

        event = getattr(record, "event", None)
        entry: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "data": payload,
        }
        if event is not None:
            entry["event"] = str(event)

        return json.dumps(entry, ensure_ascii=True, default=str)


class LogManager:
    """Public static manager for application logging use cases."""

    _lock = threading.Lock()
    _loggers: dict[str, logging.Logger] = {}
    _warned_console_fallback = False

    _max_bytes = 2 * 1024 * 1024
    _backup_count = 5

    @staticmethod
    def configure_rotation(max_bytes: int, backup_count: int) -> None:
        """Allow explicit rotation tuning for high-volume log use cases."""
        if max_bytes <= 0:
            raise ValueError("max_bytes must be > 0")
        if backup_count < 0:
            raise ValueError("backup_count must be >= 0")

        with LogManager._lock:
            LogManager._max_bytes = max_bytes
            LogManager._backup_count = backup_count
            LogManager._loggers.clear()

    @staticmethod
    def _project_root() -> Path:
        return Path(__file__).resolve().parents[3]

    @staticmethod
    def _logs_dir() -> Path:
        return LogManager._project_root() / "logs"

    @staticmethod
    def _warn_console_once(message: str) -> None:
        if LogManager._warned_console_fallback:
            return
        LogManager._warned_console_fallback = True
        print(f"[LOGGER WARNING] {message}", file=sys.stderr)

    @staticmethod
    def _is_logs_dir_writable() -> bool:
        logs_dir = LogManager._logs_dir()

        try:
            logs_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            LogManager._warn_console_once(
                f"LogManager fallback: cannot create logs directory at {logs_dir}: {exc}"
            )
            return False

        try:
            with tempfile.NamedTemporaryFile(prefix=".log_write_test_", dir=logs_dir):
                pass
        except OSError as exc:
            LogManager._warn_console_once(
                f"LogManager fallback: logs directory is not writable at {logs_dir}: {exc}"
            )
            return False

        return True

    @staticmethod
    def _build_use_case_logger(use_case: str) -> logging.Logger:
        logger = logging.getLogger(f"app.{use_case}")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        logger.handlers.clear()

        if not LogManager._is_logs_dir_writable():
            logger.addHandler(logging.NullHandler())
            return logger

        file_path = LogManager._logs_dir() / f"{use_case}.jsonl"
        handler = RotatingFileHandler(
            filename=file_path,
            maxBytes=LogManager._max_bytes,
            backupCount=LogManager._backup_count,
            encoding="utf-8",
        )
        handler.setLevel(logging.INFO)
        handler.setFormatter(_JsonlFormatter())
        logger.addHandler(handler)
        return logger

    @staticmethod
    def get_logger(use_case: str) -> logging.Logger:
        use_case_key = (use_case or "general").strip().lower().replace(" ", "_")

        with LogManager._lock:
            existing = LogManager._loggers.get(use_case_key)
            if existing is not None:
                return existing

            logger = LogManager._build_use_case_logger(use_case_key)
            LogManager._loggers[use_case_key] = logger
            return logger

    @staticmethod
    def log_event(
        use_case: str,
        event: str,
        payload: dict[str, Any] | None = None,
        level: int = logging.INFO,
        message: str = "",
    ) -> None:
        """Write a structured use-case event; never raise to callers."""
        logger = LogManager.get_logger(use_case)
        safe_payload = payload or {}

        try:
            logger.log(level, message, extra={"event": event, "payload": safe_payload})
        except Exception as exc:  # noqa: BLE001
            LogManager._warn_console_once(
                f"LogManager fallback: failed to write event '{event}' for '{use_case}': {exc}"
            )

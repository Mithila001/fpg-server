from __future__ import annotations

import logging
from typing import Any

from app.util.logger.log_manager import LogManager


class SystemLogger:
    """High-level system logger that writes to logs/system.jsonl."""

    USE_CASE = "system"

    SECTOR_MAP: dict[int, str] = {
        1: "algo_manager",
        2: "fpg_algo",
        3: "optuna",
        4: "score",
        5: "api",
    }

    @staticmethod
    def sector_name(sector: int) -> str:
        return SystemLogger.SECTOR_MAP.get(int(sector), f"unknown_sector_{sector}")

    @staticmethod
    def _safe_data(data: dict[str, Any] | None) -> dict[str, Any]:
        return data if isinstance(data, dict) else {}

    @staticmethod
    def log(
        level: int,
        sector: int,
        message: str,
        data: dict[str, Any] | None = None,
        filename: str | None = None,
    ) -> None:
        LogManager.log_event(
            use_case=SystemLogger.USE_CASE,
            event="system_log",
            payload=SystemLogger._safe_data(data),
            level=level,
            message=message,
            filename=filename or "unknown",
            sector=SystemLogger.sector_name(sector),
        )

    @staticmethod
    def info(
        sector: int,
        message: str,
        data: dict[str, Any] | None = None,
        filename: str | None = None,
    ) -> None:
        SystemLogger.log(logging.INFO, sector, message, data=data, filename=filename)

    @staticmethod
    def warning(
        sector: int,
        message: str,
        data: dict[str, Any] | None = None,
        filename: str | None = None,
    ) -> None:
        SystemLogger.log(logging.WARNING, sector, message, data=data, filename=filename)

    @staticmethod
    def error(
        sector: int,
        message: str,
        data: dict[str, Any] | None = None,
        filename: str | None = None,
    ) -> None:
        SystemLogger.log(logging.ERROR, sector, message, data=data, filename=filename)

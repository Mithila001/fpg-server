from __future__ import annotations

from typing import Any

from app.util.logger.log_manager import LogManager


class ScoreLogger:
    """Use-case logger for floor-plan scoring events only."""

    USE_CASE = "fpg_score"

    @staticmethod
    def _as_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _normalized_scores(component_scores: dict[str, Any] | None) -> dict[str, float]:
        if not isinstance(component_scores, dict):
            return {}
        return {
            str(key): round(ScoreLogger._as_float(value), 4)
            for key, value in component_scores.items()
        }

    @staticmethod
    def score_breakdown(
        component_scores: dict[str, Any] | None,
        total_score: float,
        valid: bool,
        hard_violation_count: int = 0,
    ) -> None:
        payload: dict[str, Any] = {
            **ScoreLogger._normalized_scores(component_scores),
            "total_score": round(ScoreLogger._as_float(total_score), 4),
            "valid": bool(valid),
            "hard_violation_count": int(hard_violation_count),
        }
        LogManager.log_event(ScoreLogger.USE_CASE, "score_breakdown", payload)

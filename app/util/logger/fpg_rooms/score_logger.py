from __future__ import annotations

from typing import Any

from app.util.logger.log_manager import LogManager


class ScoreLogger:
    """Use-case logger for floor-plan scoring events only."""

    USE_CASE = "fpg_score"
    SCORE_FIELDS = (
        "coverage",
        "rectangularity",
        "empty_space",
    )
    BINARY_FIELDS = (
        "room_geometry",
        "no_overlap",
        "adjacency",
        "envelope",
        "inward_pocket",
    )

    @staticmethod
    def _as_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _format_score(value: Any) -> str:
        # Keep score fields scan-friendly with fixed width (e.g. 001.25).
        numeric = ScoreLogger._as_float(value)
        return f"{round(numeric, 2):06.2f}"

    @staticmethod
    def _normalized_scores(component_scores: dict[str, Any] | None) -> dict[str, Any]:
        source = component_scores if isinstance(component_scores, dict) else {}
        normalized: dict[str, Any] = {}

        for key in ScoreLogger.SCORE_FIELDS:
            normalized[key] = ScoreLogger._format_score(source.get(key, 0.0))

        for key in ScoreLogger.BINARY_FIELDS:
            normalized[key] = bool(source.get(key, False))

        return normalized

    @staticmethod
    def score_breakdown(
        component_scores: dict[str, Any] | None,
        total_score: float,
        valid: bool,
        hard_violation_count: int = 0,
    ) -> None:
        payload: dict[str, Any] = {
            **ScoreLogger._normalized_scores(component_scores),
            "total_score": ScoreLogger._format_score(total_score),
            "valid": bool(valid),
            "hard_violation_count": int(hard_violation_count),
        }
        LogManager.log_event(ScoreLogger.USE_CASE, "score_breakdown", payload)

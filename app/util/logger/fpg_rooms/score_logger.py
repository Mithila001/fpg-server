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

    @staticmethod
    def score_component_evaluations(
        component_scores: dict[str, Any] | None,
        diagnostics: dict[str, Any] | None = None,
        stage: str = "final",
    ) -> None:
        source_scores = component_scores if isinstance(component_scores, dict) else {}
        source_diagnostics = diagnostics if isinstance(diagnostics, dict) else {}

        for key in ScoreLogger.SCORE_FIELDS:
            raw_score = ScoreLogger._as_float(source_scores.get(key, 0.0))
            payload: dict[str, Any] = {
                "component": key,
                "score_type": "range",
                "score": ScoreLogger._format_score(raw_score),
                "raw_score": round(raw_score, 6),
                "stage": stage,
                "diagnostic": source_diagnostics.get(key),
            }
            LogManager.log_event(ScoreLogger.USE_CASE, "score_component", payload)

        for key in ScoreLogger.BINARY_FIELDS:
            passed = bool(source_scores.get(key, False))
            payload = {
                "component": key,
                "score_type": "binary",
                "passed": passed,
                "score": ScoreLogger._format_score(1.0 if passed else 0.0),
                "raw_score": 1.0 if passed else 0.0,
                "stage": stage,
            }
            LogManager.log_event(ScoreLogger.USE_CASE, "score_component", payload)

    @staticmethod
    def score_run(
        component_scores: dict[str, Any] | None,
        total_score: float,
        valid: bool,
        hard_violation_count: int = 0,
        diagnostics: dict[str, Any] | None = None,
        stage: str = "final",
    ) -> None:
        source_scores = component_scores if isinstance(component_scores, dict) else {}
        source_diagnostics = diagnostics if isinstance(diagnostics, dict) else {}

        range_scores: dict[str, Any] = {}
        for key in ScoreLogger.SCORE_FIELDS:
            raw_score = ScoreLogger._as_float(source_scores.get(key, 0.0))
            range_scores[key] = {
                "score": ScoreLogger._format_score(raw_score),
                "raw_score": round(raw_score, 6),
                "diagnostic": source_diagnostics.get(key),
            }

        binary_scores: dict[str, Any] = {}
        for key in ScoreLogger.BINARY_FIELDS:
            passed = bool(source_scores.get(key, False))
            binary_scores[key] = {
                "passed": passed,
                "score": ScoreLogger._format_score(1.0 if passed else 0.0),
                "raw_score": 1.0 if passed else 0.0,
            }

        payload: dict[str, Any] = {
            "stage": stage,
            "range_scores": range_scores,
            "binary_scores": binary_scores,
            "total_score": ScoreLogger._format_score(total_score),
            "total_raw_score": round(ScoreLogger._as_float(total_score), 6),
            "valid": bool(valid),
            "hard_violation_count": int(hard_violation_count),
            "geometric_gate_violations": source_diagnostics.get("geometric_gate_violations", []),
            "weights": source_diagnostics.get("weights", {}),
        }

        LogManager.log_event(ScoreLogger.USE_CASE, "score_run", payload)

from __future__ import annotations

from typing import Any

from app.algorithms.fpg_rooms.types.room import FpgRequirements

from app.util.logger.log_manager import LogManager


class OptunaLogger:
    """Use-case logger for Optuna optimization events."""

    USE_CASE = "optuna"

    @staticmethod
    def _trial_payload_base(trial_number: int, requirements: FpgRequirements) -> dict[str, Any]:
        return {
            "trial_number": int(trial_number),
            "hallway_count": int(getattr(requirements.config, "hallway_count", 0)),
            "min_coverage": float(getattr(requirements.config, "min_coverage", 0.0)),
        }

    @staticmethod
    def trial_start(trial_number: int, requirements: FpgRequirements) -> None:
        payload = OptunaLogger._trial_payload_base(trial_number, requirements)
        LogManager.log_event(OptunaLogger.USE_CASE, "trial_start", payload)

    @staticmethod
    def precheck_failed(
        trial_number: int,
        requirements: FpgRequirements,
        reason: str,
    ) -> None:
        payload = OptunaLogger._trial_payload_base(trial_number, requirements)
        payload.update({"reason": reason})
        LogManager.log_event(OptunaLogger.USE_CASE, "precheck_failed", payload)

    @staticmethod
    def evaluation_done(
        trial_number: int,
        requirements: FpgRequirements,
        status: str,
        solved: bool,
        valid: bool,
        score: float | None,
        hard_violation_count: int,
        message: str,
    ) -> None:
        payload = OptunaLogger._trial_payload_base(trial_number, requirements)
        payload.update(
            {
                "status": status,
                "solved": bool(solved),
                "valid": bool(valid),
                "score": score,
                "hard_violation_count": int(hard_violation_count),
                "message": message,
            }
        )
        LogManager.log_event(OptunaLogger.USE_CASE, "evaluation_done", payload)

    @staticmethod
    def optimization_summary(
        study_name: str,
        best_trial_number: int,
        best_value: float,
        completed_trials: int,
        failed_trials: int,
        best_params: dict[str, Any],
        best_status: str,
        best_solved: bool,
    ) -> None:
        payload = {
            "study_name": study_name,
            "best_trial_number": int(best_trial_number),
            "best_value": float(best_value),
            "completed_trials": int(completed_trials),
            "failed_trials": int(failed_trials),
            "best_params": dict(best_params),
            "best_status": best_status,
            "best_solved": bool(best_solved),
        }
        LogManager.log_event(OptunaLogger.USE_CASE, "optimization_summary", payload)

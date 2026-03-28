from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.algorithms.fpg_rooms.fpg_score.types import ScoreReport


@dataclass
class FpgEvaluationResult:
    solved: bool
    solution: list[dict[str, Any]] = field(default_factory=list)
    score_report: ScoreReport | None = None
    status: str = "UNKNOWN"
    message: str = ""


@dataclass
class OptunaOptimizationResult:
    study_name: str
    best_value: float
    best_trial_number: int
    best_params: dict[str, Any] = field(default_factory=dict)
    completed_trials: int = 0
    failed_trials: int = 0
    best_run: FpgEvaluationResult | None = None

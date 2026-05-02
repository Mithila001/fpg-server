from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.algorithms.types.fpg_score import ScoreManagerResult
from app.util.algorithm_manager.fpg_procesors.union_floor_plan import (
    UnionFloorPlanResult,
)


@dataclass
class FpgEvaluationResult:
    solved: bool
    status: str = "UNKNOWN"
    message: str = ""
    fpg_score_results: ScoreManagerResult | None = None
    union_results: UnionFloorPlanResult | None = None


@dataclass
class OptunaOptimizationResult:
    study_name: str
    best_value: float
    best_trial_number: int
    best_params: dict[str, Any] = field(default_factory=dict)
    completed_trials: int = 0
    failed_trials: int = 0
    best_run: FpgEvaluationResult | None = None
    termination_reason: str = "completed"

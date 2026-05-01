from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.algorithms.fpg_rooms.fpg_score import ScoreReport
from ..openings import OpeningRunResult
from app.algorithms.types.fpg_score import ScoreManagerResult
from app.util.algorithm_manager.fpg_procesors.union_floor_plan import (
    UnionFloorPlanResult,
)


@dataclass
class FpgEvaluationResult:
    solved: bool
    solution: list[dict[str, Any]] = field(default_factory=list)
    score_report: ScoreReport | None = None
    # New: results from the newer scoring pipeline (score_manager)
    fpg_score_results: ScoreManagerResult | int | None = None
    # New: union of the floor plan (shared wall network + original floor_plan_with_openings)
    union_results: UnionFloorPlanResult | None = None
    status: str = "UNKNOWN"
    message: str = ""
    quick_post_process_result: dict[str, Any] | None = None
    opening_result: OpeningRunResult | None = None
    # Serialized copy of the floor_plan_with_openings when available (helper for API)
    floor_plan_with_openings: dict[str, Any] | None = None
    refine_status: str = ""
    refine_message: str = ""


@dataclass
class OptunaOptimizationResult:
    study_name: str
    best_value: float
    best_trial_number: int
    best_params: dict[str, Any] = field(default_factory=dict)
    completed_trials: int = 0
    failed_trials: int = 0
    best_run: FpgEvaluationResult | None = None

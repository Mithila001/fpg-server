from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from app.algorithms.floor_plan_preprocessing import (
    PreprocessingReferenceData,
    ReferenceDataError,
)
from app.algorithms.floor_plan_scoring import FloorPlanScoringResult
from app.algorithms.types_new import FloorPlan, RoomType
from app.core.execution import ExecutionContext
from app.visualization.features.score.config import ScoringVisualizationConfig


class GenerationStage(str, Enum):
    CANCELLATION = "cancellation"
    PREPROCESSING = "preprocessing"
    CANDIDATE_SEARCH = "candidate_search"
    CANDIDATE_SCORING = "candidate_scoring"
    SOLVER = "solver"
    REFINEMENT = "refinement"
    POST_PROCESSING = "post_processing"
    OPENINGS = "openings"
    ATTEMPT_SCORING = "attempt_scoring"
    SCORING = "scoring"
    VISUALIZATION = "visualization"
    FINAL_VALIDATION = "final_validation"


@dataclass(frozen=True, slots=True)
class RequestedGenerationRoom:
    room_type: RoomType
    id: str | None = None
    name: str | None = None
    requested_size: str | None = "regular"

    def __post_init__(self) -> None:
        if not isinstance(self.room_type, RoomType):
            raise TypeError("room_type must be a RoomType enum member")


@dataclass(frozen=True, slots=True)
class GenerationPipelineRequest:
    request_id: str
    max_width: float
    max_length: float
    aspect_ratio: float | str
    rooms: tuple[RequestedGenerationRoom, ...]
    execution_context: ExecutionContext | None = None


@dataclass(frozen=True, slots=True)
class GenerationPipelineSettings:
    """Tuning values for the search -> solve -> score orchestration loop."""

    candidate_search_enabled: bool = True
    candidate_score_threshold: float = 75.0
    candidate_trial_count: int = 500
    candidate_grid_resolution: float = 20
    candidate_random_seed: int | None = None

    timeout_seconds: float = 60.0
    usable_floor_plan_score: float = 80.0
    presentable_floor_plan_score: float = 90.0
    solver_runs_per_candidate: int = 2

    render_candidate_search: bool = True
    render_solver_attempts: bool = True
    scoring_visualization: ScoringVisualizationConfig = field(
        default_factory=ScoringVisualizationConfig
    )
    require_final_critical_pass: bool = True

    # Temporary migration aliases for existing callers. Remove after callers
    # have moved to solver_runs_per_candidate/presentable_floor_plan_score.
    solver_max_attempts: int | None = None
    target_floor_plan_score: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.scoring_visualization, ScoringVisualizationConfig):
            raise TypeError(
                "scoring_visualization must be a ScoringVisualizationConfig"
            )
        if isinstance(self.candidate_trial_count, bool) or not isinstance(
            self.candidate_trial_count,
            int,
        ):
            raise TypeError("candidate_trial_count must be an integer")
        if self.candidate_trial_count <= 0:
            raise ValueError("candidate_trial_count must be greater than zero")

        _require_positive_finite(
            "candidate_grid_resolution",
            self.candidate_grid_resolution,
        )
        _require_finite("candidate_score_threshold", self.candidate_score_threshold)
        _require_positive_finite("timeout_seconds", self.timeout_seconds)
        _require_finite("usable_floor_plan_score", self.usable_floor_plan_score)
        _require_finite(
            "presentable_floor_plan_score",
            self.presentable_floor_plan_score,
        )

        if isinstance(self.solver_runs_per_candidate, bool) or not isinstance(
            self.solver_runs_per_candidate,
            int,
        ):
            raise TypeError("solver_runs_per_candidate must be an integer")
        if self.solver_runs_per_candidate <= 0:
            raise ValueError("solver_runs_per_candidate must be greater than zero")

        if self.solver_max_attempts is not None:
            if isinstance(self.solver_max_attempts, bool) or not isinstance(
                self.solver_max_attempts,
                int,
            ):
                raise TypeError("solver_max_attempts must be an integer or None")
            if self.solver_max_attempts <= 0:
                raise ValueError("solver_max_attempts must be greater than zero")

        if self.target_floor_plan_score is not None:
            _require_finite(
                "target_floor_plan_score",
                self.target_floor_plan_score,
            )

        if self.effective_presentable_floor_plan_score < self.usable_floor_plan_score:
            raise ValueError(
                "presentable floor-plan score cannot be below usable floor-plan score"
            )

    @property
    def effective_solver_runs_per_candidate(self) -> int:
        return (
            self.solver_max_attempts
            if self.solver_max_attempts is not None
            else self.solver_runs_per_candidate
        )

    @property
    def effective_presentable_floor_plan_score(self) -> float:
        return (
            float(self.target_floor_plan_score)
            if self.target_floor_plan_score is not None
            else float(self.presentable_floor_plan_score)
        )


@dataclass(frozen=True, slots=True)
class GenerationPipelineResult:
    floor_plan: FloorPlan
    scoring: FloorPlanScoringResult
    execution_context: ExecutionContext | None = None


class GenerationPipelineError(Exception):
    def __init__(
        self,
        stage: GenerationStage,
        code: str,
        message: str,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.stage = stage
        self.code = code
        self.message = message
        self.details = MappingProxyType(dict(details or {}))


REFERENCE_DATA_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "generation_reference_data.json"
)


def load_generation_reference_data(
    path: Path = REFERENCE_DATA_PATH,
) -> PreprocessingReferenceData:
    """Compatibility facade for callers migrating to the complete core config."""
    try:
        from app.core_config import CoreConfigLoadError, load_fpg_core_config

        return load_fpg_core_config(generation_path=path).preprocessing
    except (CoreConfigLoadError, OSError, ValueError) as exc:
        raise ReferenceDataError(
            f"Could not load generation reference data from '{path}': {exc}"
        ) from exc


def _require_finite(field_name: str, value: float) -> None:
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be numeric")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{field_name} must be numeric") from exc
    if not math.isfinite(numeric):
        raise ValueError(f"{field_name} must be finite")


def _require_positive_finite(field_name: str, value: float) -> None:
    _require_finite(field_name, value)
    if float(value) <= 0:
        raise ValueError(f"{field_name} must be greater than zero")

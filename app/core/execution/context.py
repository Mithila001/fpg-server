from __future__ import annotations

import os
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any

from .enums import PipelineStage
from .ids import CandidateId, FlowId, SearchTrialId, SolverRunId
from .naming import flow_id_for


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    flow_id: FlowId
    flow_started_at: datetime
    job_id: str | None = None
    pipeline_stage: PipelineStage | None = None
    search_trial_id: SearchTrialId | None = None
    candidate_id: CandidateId | None = None
    solver_run_id: SolverRunId | None = None
    parent_flow_id: FlowId | None = None
    process_id: int | None = None
    worker_id: str | None = None
    seed: int | None = None

    def __post_init__(self) -> None:
        if not str(self.flow_id).strip():
            raise ValueError("flow_id cannot be empty")
        started = self.flow_started_at
        if started.tzinfo is None:
            object.__setattr__(self, "flow_started_at", started.replace(tzinfo=UTC))
        else:
            object.__setattr__(self, "flow_started_at", started.astimezone(UTC))
        for field_name in ("search_trial_id", "candidate_id", "solver_run_id"):
            value = getattr(self, field_name)
            if value is not None and (isinstance(value, bool) or int(value) < 0):
                raise ValueError(f"{field_name} must be a non-negative integer")

    @classmethod
    def create_root(
        cls,
        *,
        job_id: str | None = None,
        started_at: datetime | None = None,
        seed: int | None = None,
        flow_sequence: int = 1,
    ) -> "ExecutionContext":
        current = started_at or datetime.now(UTC)
        return cls(
            flow_id=FlowId(
                flow_id_for(started_at=current, sequence=flow_sequence)
            ),
            flow_started_at=current,
            job_id=job_id,
            process_id=os.getpid(),
            seed=seed,
        )

    def with_stage(self, stage: PipelineStage) -> "ExecutionContext":
        if not isinstance(stage, PipelineStage):
            raise TypeError("stage must be a PipelineStage")
        return replace(self, pipeline_stage=stage)

    def for_search_trial(self, trial_id: int) -> "ExecutionContext":
        _validate_identifier("search_trial_id", trial_id)
        return replace(
            self,
            search_trial_id=SearchTrialId(trial_id),
            candidate_id=None,
            solver_run_id=None,
        )

    def for_candidate(self, candidate_id: int) -> "ExecutionContext":
        _validate_identifier("candidate_id", candidate_id)
        if candidate_id < 1:
            raise ValueError("candidate_id must be greater than zero")
        return replace(
            self,
            candidate_id=CandidateId(candidate_id),
            solver_run_id=None,
        )

    def for_solver_run(self, solver_run_id: int) -> "ExecutionContext":
        _validate_identifier("solver_run_id", solver_run_id)
        if solver_run_id < 1:
            raise ValueError("solver_run_id must be greater than zero")
        if self.candidate_id is None:
            raise ValueError("solver runs require a candidate_id")
        return replace(self, solver_run_id=SolverRunId(solver_run_id))

    def to_dict(self) -> dict[str, Any]:
        return {
            "flow_id": str(self.flow_id),
            "flow_started_at": self.flow_started_at.isoformat(),
            "job_id": self.job_id,
            "pipeline_stage": (
                self.pipeline_stage.value if self.pipeline_stage is not None else None
            ),
            "search_trial_id": (
                int(self.search_trial_id)
                if self.search_trial_id is not None
                else None
            ),
            "candidate_id": (
                int(self.candidate_id) if self.candidate_id is not None else None
            ),
            "solver_run_id": (
                int(self.solver_run_id) if self.solver_run_id is not None else None
            ),
            "parent_flow_id": (
                str(self.parent_flow_id) if self.parent_flow_id is not None else None
            ),
            "process_id": self.process_id,
            "worker_id": self.worker_id,
            "seed": self.seed,
        }


def _validate_identifier(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")

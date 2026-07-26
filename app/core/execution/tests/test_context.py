from __future__ import annotations

import pickle
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from app.core.execution import ExecutionContext, PipelineStage, flow_directory_name


def test_context_derives_distinct_typed_identities_without_mutation() -> None:
    root = ExecutionContext.create_root(
        job_id="job-1842",
        started_at=datetime(2026, 7, 25, 18, 31, 52, 481000, tzinfo=UTC),
    )
    trial = root.with_stage(PipelineStage.CANDIDATE_SEARCH).for_search_trial(4)
    candidate = trial.for_candidate(2)
    solver = candidate.for_solver_run(1)

    assert root.search_trial_id is None
    assert solver.search_trial_id is not None
    assert solver.candidate_id is not None
    assert solver.solver_run_id is not None
    assert int(solver.search_trial_id) == 4
    assert int(solver.candidate_id) == 2
    assert int(solver.solver_run_id) == 1
    assert flow_directory_name(
        started_at=root.flow_started_at,
        flow_id=str(root.flow_id),
    ) == "20260725T183152.481Z_flow"
    assert str(root.flow_id) == "flow_20260725T183152.481Z"
    assert "job-1842" not in str(root.flow_id)


def test_context_is_frozen_serializable_and_picklable() -> None:
    context = ExecutionContext.create_root(job_id="job-1").for_candidate(1)
    with pytest.raises(FrozenInstanceError):
        context.job_id = "changed"  # type: ignore[misc]

    restored = pickle.loads(pickle.dumps(context))
    assert restored == context
    assert restored.to_dict()["candidate_id"] == 1


@pytest.mark.parametrize("value", [-1, True, 1.5])
def test_context_rejects_invalid_identifiers(value: object) -> None:
    context = ExecutionContext.create_root(job_id="job-1")
    expected = TypeError if value is True or isinstance(value, float) else ValueError
    with pytest.raises(expected):
        context.for_search_trial(value)  # type: ignore[arg-type]


def test_solver_run_requires_candidate_identity() -> None:
    with pytest.raises(ValueError, match="candidate_id"):
        ExecutionContext.create_root(job_id="job-1").for_solver_run(1)


def test_candidate_and_solver_ids_are_one_based() -> None:
    context = ExecutionContext.create_root(job_id="job-1")
    with pytest.raises(ValueError, match="greater than zero"):
        context.for_candidate(0)
    with pytest.raises(ValueError, match="greater than zero"):
        context.for_candidate(1).for_solver_run(0)

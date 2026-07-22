from __future__ import annotations

from typing import Any

from app.algorithms.candidate_search import (
    CandidatePoint,
    CandidateSearchResult,
    CandidateSearchSettings,
)
from app.pipeline.generation import pipeline


def test_best_candidate_visualization_contains_attempt_and_search_metadata(
    monkeypatch: Any,
) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        pipeline,
        "render_candidate_search",
        lambda payload, **kwargs: calls.append(
            {"payload": payload, "kwargs": kwargs}
        ),
    )
    result = CandidateSearchResult(
        points=(CandidatePoint("living-room", 20, 30),),
        score=87.5,
        completed_trials=12,
    )
    settings = CandidateSearchSettings(
        min_x=0,
        max_x=120,
        min_y=0,
        max_y=90,
        grid_resolution=5,
        trial_count=12,
        random_seed=42,
    )

    pipeline._render_candidate_search_result(
        request_id="request-42",
        attempt_number=2,
        result=result,
        settings=settings,
        run_timestamp="20260722T061530123456Z",
    )

    assert len(calls) == 1
    payload = calls[0]["payload"]
    assert payload.score == 87.5
    assert payload.metadata == {
        "attempt_number": 2,
        "completed_trials": 12,
        "result": "best_candidate",
    }
    assert calls[0]["kwargs"] == {
        "run_id": "request-42",
        "run_timestamp": "20260722T061530123456Z",
        "output_name": "attempt-2-best-candidate",
    }

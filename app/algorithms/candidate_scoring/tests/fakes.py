from __future__ import annotations

from collections.abc import Mapping, MutableSequence
from typing import Any

from app.algorithms.candidate_scoring.context import ScoringContext
from app.algorithms.candidate_scoring.evaluators.base import CandidateEvaluator
from app.algorithms.candidate_scoring.types import (
    EvaluationStatus,
    EvaluatorKey,
    EvaluatorResult,
    ScoreFinding,
)


class FakeEvaluator(CandidateEvaluator):
    """Configurable evaluator used to isolate score-manager behavior."""

    def __init__(
        self,
        key: str,
        *,
        score: float | None = 100.0,
        status: EvaluationStatus = EvaluationStatus.COMPLETED,
        returned_key: str | None = None,
        findings: tuple[ScoreFinding, ...] = (),
        metrics: Mapping[str, float] | None = None,
        error: Exception | None = None,
        execution_log: MutableSequence[str] | None = None,
    ) -> None:
        self._key = EvaluatorKey(key)
        self._score = score
        self._status = status
        self._returned_key = EvaluatorKey(returned_key or key)
        self._findings = findings
        self._metrics = dict(metrics or {})
        self._error = error
        self._execution_log = execution_log
        self.call_count = 0
        self.received_contexts: list[ScoringContext] = []
        self.received_settings: list[Mapping[str, Any]] = []

    @property
    def key(self) -> EvaluatorKey:
        return self._key

    def evaluate(
        self,
        context: ScoringContext,
        settings: Mapping[str, Any],
    ) -> EvaluatorResult:
        self.call_count += 1
        self.received_contexts.append(context)
        self.received_settings.append(settings)
        if self._execution_log is not None:
            self._execution_log.append(str(self.key))
        if self._error is not None:
            raise self._error

        return EvaluatorResult(
            evaluator_key=self._returned_key,
            status=self._status,
            score=self._score,
            findings=self._findings,
            metrics=self._metrics,
        )

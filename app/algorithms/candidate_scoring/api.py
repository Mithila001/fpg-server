from __future__ import annotations

from .config import ScoringConfig
from .context import ScoringContextFactory
from .logging import (
    CandidateScoringEvent,
    log_candidate_scoring_event,
    record_candidate_scoring_result,
)
from .manager import CandidateScoreManager
from .registry import EvaluatorRegistry
from .types import CandidateScoringInput, ScoringResult


def evaluate_candidate(
    scoring_input: CandidateScoringInput,
    *,
    registry: EvaluatorRegistry,
    config: ScoringConfig,
    context_factory: ScoringContextFactory | None = None,
) -> ScoringResult:
    """Public one-shot API for candidate scoring."""

    context = scoring_input.execution_context
    log_candidate_scoring_event(context, CandidateScoringEvent.STARTED)
    try:
        manager = CandidateScoreManager(
            registry=registry,
            config=config,
            context_factory=context_factory,
        )
        result = manager.score(scoring_input)
    except Exception as exc:
        log_candidate_scoring_event(
            context,
            CandidateScoringEvent.FAILED,
            level="ERROR",
            exception=exc,
        )
        raise
    record_candidate_scoring_result(context, result)
    return result

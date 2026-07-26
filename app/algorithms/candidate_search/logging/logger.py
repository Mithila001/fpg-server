from __future__ import annotations

from typing import Any

from app.artifacts import FeatureKey
from app.core.execution import ExecutionContext
from app.util.logger import BaseLogger, LogLevel

from .events import CandidateSearchEvent


def log_candidate_search_event(
    context: ExecutionContext | None,
    event: CandidateSearchEvent,
    *,
    level: str = "INFO",
    payload: dict[str, Any] | None = None,
    exception: BaseException | None = None,
) -> None:
    if context is None:
        return
    BaseLogger().log(
        feature=FeatureKey.CANDIDATE_SEARCH,
        event=event.value,
        level=LogLevel(level),
        context=context,
        payload=payload,
        exception=exception,
    )

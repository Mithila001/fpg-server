from __future__ import annotations

from typing import Any

from app.artifacts import FeatureKey
from app.core.execution import ExecutionContext
from app.util.logger import BaseLogger, LogLevel


def log_post_processing_event(
    context: ExecutionContext | None,
    event: str,
    level: str,
    data: dict[str, Any] | None = None,
) -> None:
    if context is None:
        return
    BaseLogger().log(
        feature=FeatureKey.FLOOR_PLAN_POST_PROCESSING,
        event=event,
        level=LogLevel(level),
        context=context,
        payload=data,
    )


class PostProcessingLogger:
    def __init__(self, context: ExecutionContext | None) -> None:
        self.context = context

    def log_event(
        self,
        tag: str,
        event: str,
        level: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        del tag
        log_post_processing_event(self.context, event, level, data)

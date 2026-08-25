from __future__ import annotations

from app.artifacts import FeatureKey
from app.core.execution import ExecutionContext
from app.util.logger import BaseLogger, LogLevel

from .events import BuildableSpaceEvent


def log_buildable_space_event(
    context: ExecutionContext,
    event: BuildableSpaceEvent,
    *,
    level: str = "INFO",
    payload: dict[str, object] | None = None,
    exception: BaseException | None = None,
) -> None:
    BaseLogger().log(
        feature=FeatureKey.BUILDABLE_SPACE,
        event=event.value,
        level=LogLevel(level),
        context=context,
        payload=payload,
        exception=exception,
    )

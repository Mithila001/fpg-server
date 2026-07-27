from __future__ import annotations

from app.artifacts import FeatureKey
from app.core.execution import ExecutionContext
from app.util.logger import BaseLogger, LogLevel

from .events import UsableLandEvent


def log_usable_land_event(
    context: ExecutionContext | None,
    event: UsableLandEvent,
    *,
    level: str = "INFO",
    payload: dict[str, object] | None = None,
    exception: BaseException | None = None,
) -> None:
    if context is None:
        return
    BaseLogger().log(
        feature=FeatureKey.USABLE_LAND,
        event=event.value,
        level=LogLevel(level),
        context=context,
        payload=payload,
        exception=exception,
    )

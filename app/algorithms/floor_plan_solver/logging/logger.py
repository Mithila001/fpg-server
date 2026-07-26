from __future__ import annotations

from app.artifacts import FeatureKey
from app.core.execution import ExecutionContext
from app.util.logger import BaseLogger, LogLevel

from .events import FloorPlanSolverEvent


def log_solver_event(
    context: ExecutionContext | None,
    event: FloorPlanSolverEvent,
    *,
    level: str = "INFO",
    payload: dict[str, object] | None = None,
    exception: BaseException | None = None,
) -> None:
    if context is None:
        return
    BaseLogger().log(
        feature=FeatureKey.FLOOR_PLAN_SOLVER,
        event=event.value,
        level=LogLevel(level),
        context=context,
        payload=payload,
        exception=exception,
    )

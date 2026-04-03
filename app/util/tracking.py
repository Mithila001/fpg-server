from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator


REQUEST_ID_FORMAT = "%Y%m%d-%H-%M-%S"
TRIAL_ID_WIDTH = 4


@dataclass
class PipelineTrackingContext:
    request_id: str
    trial_index: int = 0
    trial_id: str | None = None

    def next_trial_id(self) -> str:
        self.trial_index += 1
        self.trial_id = f"{self.trial_index:0{TRIAL_ID_WIDTH}d}"
        return self.trial_id

    def clear_trial_id(self) -> None:
        self.trial_id = None


_current_tracking_context: ContextVar[PipelineTrackingContext | None] = ContextVar(
    "pipeline_tracking_context",
    default=None,
)


def generate_request_id(now: datetime | None = None) -> str:
    moment = now or datetime.now()
    return moment.strftime(REQUEST_ID_FORMAT)


def get_tracking_context() -> PipelineTrackingContext | None:
    return _current_tracking_context.get()


def get_tracking_ids() -> tuple[str | None, str | None]:
    context = get_tracking_context()
    if context is None:
        return None, None
    return context.request_id, context.trial_id


def get_tracking_label() -> str | None:
    context = get_tracking_context()
    if context is None:
        return None

    label_parts = [f"request={context.request_id}"]
    if context.trial_id is not None:
        label_parts.append(f"trial={context.trial_id}")
    return " | ".join(label_parts)


@contextmanager
def use_tracking_context(request_id: str | None = None) -> Iterator[PipelineTrackingContext]:
    context = PipelineTrackingContext(request_id=request_id or generate_request_id())
    token = _current_tracking_context.set(context)
    try:
        yield context
    finally:
        _current_tracking_context.reset(token)
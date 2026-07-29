from __future__ import annotations

from threading import Event, Lock
from typing import Protocol


class GenerationCancellationSignal(Protocol):
    """Read-only cancellation state consumed by the generation pipeline."""

    @property
    def is_cancelled(self) -> bool: ...

    @property
    def reason(self) -> str | None: ...


class GenerationCancellationToken:
    """Thread-safe cooperative cancellation token for one generation job."""

    def __init__(self) -> None:
        self._cancelled = Event()
        self._lock = Lock()
        self._reason: str | None = None

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()

    @property
    def reason(self) -> str | None:
        with self._lock:
            return self._reason

    def request_cancellation(self, *, reason: str) -> bool:
        normalized_reason = reason.strip()
        if not normalized_reason:
            raise ValueError("Cancellation reason cannot be empty")

        with self._lock:
            if self._cancelled.is_set():
                return False
            self._reason = normalized_reason
            self._cancelled.set()
            return True

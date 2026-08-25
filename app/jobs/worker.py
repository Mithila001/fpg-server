from __future__ import annotations

from dataclasses import dataclass
from multiprocessing.synchronize import Event as ProcessEvent
from pathlib import Path
from typing import Any

from app.artifacts.serializers import to_json_value
from app.core_config import load_server_config
from app.pipeline.generation import (
    GenerationPipelineError,
    GenerationPipelineRequest,
    run_generation_pipeline,
)
from app.streaming import GenerationEventPublisher, WorkerEvent


@dataclass(frozen=True, slots=True)
class WorkerFinished:
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    termination_reason: str | None = None


class QueuePublisher(GenerationEventPublisher):
    def __init__(self, queue: Any) -> None:
        self._queue = queue

    def publish(self, event: WorkerEvent) -> None:
        self._queue.put(event)


def run_generation_worker(
    request: GenerationPipelineRequest,
    config_path: str,
    queue: Any,
    cancellation: ProcessEvent,
) -> None:
    try:
        result = run_generation_pipeline(
            request,
            load_server_config(path=Path(config_path)),
            QueuePublisher(queue),
            cancellation,
        )
        value = to_json_value(result)
        queue.put(
            WorkerFinished(
                result=value if isinstance(value, dict) else {"result": value}
            )
        )
    except GenerationPipelineError as exc:
        reason = exc.details.get("termination_reason")
        queue.put(
            WorkerFinished(
                error={
                    "stage": exc.stage.value,
                    "code": exc.code,
                    "message": exc.message,
                    "details": to_json_value(dict(exc.details)),
                },
                termination_reason=str(reason) if reason is not None else None,
            )
        )
    except BaseException as exc:
        queue.put(
            WorkerFinished(
                error={
                    "stage": "generation",
                    "code": "unexpected_generation_error",
                    "message": str(exc),
                    "details": {"exception_type": type(exc).__name__},
                }
            )
        )

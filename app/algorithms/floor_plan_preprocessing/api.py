from __future__ import annotations

from .contracts import PreparedGenerationInput, PreprocessingInput
from .logging import PreprocessingEvent, log_preprocessing_event
from .pipeline import run_pipeline


def prepare_generation_input(
    input: PreprocessingInput,
) -> PreparedGenerationInput:
    """Prepare one trusted generation specification without external side effects."""

    context = input.execution_context
    log_preprocessing_event(
        context,
        PreprocessingEvent.STARTED,
        payload={"requested_room_count": len(input.request.rooms)},
    )
    try:
        result = run_pipeline(input)
    except Exception as exc:
        log_preprocessing_event(
            context,
            PreprocessingEvent.FAILED,
            level="ERROR",
            exception=exc,
        )
        raise
    log_preprocessing_event(
        context,
        PreprocessingEvent.COMPLETED,
        payload={"prepared_room_count": len(result.generation_spec.rooms)},
    )
    return result

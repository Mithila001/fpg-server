from enum import StrEnum


class PostProcessingEvent(StrEnum):
    STARTED = "post_processing_started"
    COMPLETED = "post_processing_completed"
    FAILED = "post_processing_failed"
    PROCESSOR_STARTED = "processor_started"
    PROCESSOR_COMPLETED = "processor_completed"
    PROCESSOR_FAILED = "processor_failed"

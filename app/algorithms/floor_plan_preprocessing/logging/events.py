from enum import StrEnum


class PreprocessingEvent(StrEnum):
    STARTED = "preprocessing_started"
    COMPLETED = "preprocessing_completed"
    FAILED = "preprocessing_failed"

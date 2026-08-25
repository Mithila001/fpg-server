from enum import StrEnum


class BuildableSpaceEvent(StrEnum):
    STARTED = "buildable_space_started"
    REFERENCE_DATA_LOADED = "reference_data_loaded"
    REQUEST_NORMALIZED = "request_normalized"
    REQUEST_VALIDATED = "request_validated"
    COMPLETED = "buildable_space_completed"
    FAILED = "buildable_space_failed"

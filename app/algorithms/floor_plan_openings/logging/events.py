from enum import StrEnum


class FloorPlanOpeningsEvent(StrEnum):
    STARTED = "openings_started"
    COMPLETED = "openings_completed"
    FAILED = "openings_failed"

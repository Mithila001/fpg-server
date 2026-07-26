from enum import StrEnum


class FloorPlanScoringEvent(StrEnum):
    STARTED = "scoring_started"
    COMPLETED = "scoring_completed"
    FAILED = "scoring_failed"
    RESULT_RECORDED = "result_recorded"
    ARTIFACT_FAILED = "artifact_failed"

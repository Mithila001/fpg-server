from enum import StrEnum


class CandidateScoringEvent(StrEnum):
    STARTED = "scoring_started"
    COMPLETED = "scoring_completed"
    FAILED = "scoring_failed"
    ARTIFACT_FAILED = "artifact_failed"

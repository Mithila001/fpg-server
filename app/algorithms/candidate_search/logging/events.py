from enum import StrEnum


class CandidateSearchEvent(StrEnum):
    SESSION_STARTED = "session_started"
    TRIAL_SUGGESTED = "trial_suggested"
    TRIAL_COMPLETED = "trial_completed"
    TRIAL_FAILED = "trial_failed"

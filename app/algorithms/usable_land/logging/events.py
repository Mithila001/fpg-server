from enum import StrEnum


class UsableLandEvent(StrEnum):
    SEARCH_STARTED = "usable_land_search_started"
    CANDIDATES_EVALUATED = "usable_land_candidate_evaluated"
    FOUND = "usable_land_found"
    NOT_FOUND = "usable_land_not_found"
    SEARCH_FAILED = "usable_land_search_failed"

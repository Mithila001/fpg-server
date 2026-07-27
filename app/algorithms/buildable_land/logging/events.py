from enum import StrEnum


class BuildableLandEvent(StrEnum):
    EDGE_CLASSIFICATION_COMPLETED = "edge_classification_completed"
    EDGE_SETBACKS_RESOLVED = "edge_setbacks_resolved"
    CALCULATION_STARTED = "buildable_land_calculation_started"
    CALCULATION_COMPLETED = "buildable_land_calculation_completed"
    CALCULATION_FAILED = "buildable_land_calculation_failed"

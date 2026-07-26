from enum import StrEnum


class FloorPlanSolverEvent(StrEnum):
    STARTED = "solver_started"
    COMPLETED = "solver_completed"
    FAILED = "solver_failed"

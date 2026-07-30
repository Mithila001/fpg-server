from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from fpg_core.types_new import FloorPlan


class FloorPlanSolverStatus(str, Enum):
    """Solver outcomes that contain a floor plan and can be rendered."""

    OPTIMAL = "optimal"
    FEASIBLE = "feasible"


@dataclass(frozen=True, slots=True)
class FloorPlanSolverVisualization:
    """Complete typed input required to render one solver profile result."""

    floor_plan: FloorPlan
    profile_name: str
    status: FloorPlanSolverStatus

    def __post_init__(self) -> None:
        if not isinstance(self.floor_plan, FloorPlan):
            raise TypeError("floor_plan must be a types_new.FloorPlan instance")
        if not isinstance(self.status, FloorPlanSolverStatus):
            raise TypeError("status must be a FloorPlanSolverStatus value")
        if not self.profile_name.strip():
            raise ValueError("profile_name cannot be empty")
        if len(self.floor_plan.boundary.points) < 3:
            raise ValueError("floor_plan boundary must contain at least three points")
        for room in self.floor_plan.rooms:
            if len(room.boundary.points) < 3:
                raise ValueError(
                    f"room {room.id!s} boundary must contain at least three points"
                )

"""Project-domain import seam for the CP-SAT floor-plan solver.

Only this module should import the application's shared floor-plan types. If the
shared types are moved or re-exported differently, update this file and leave
the solver internals unchanged.
"""

from app.algorithms.types.domain import (
    ConstraintStrength,
    FloorPlan,
    FloorPlanGenerationSpec,
    FloorPlanRoom,
    MatchPolicy,
    Point,
    Polygon,
    RoomId,
    RoomType,
)

__all__ = [
    "ConstraintStrength",
    "FloorPlan",
    "FloorPlanGenerationSpec",
    "FloorPlanRoom",
    "MatchPolicy",
    "Point",
    "Polygon",
    "RoomId",
    "RoomType",
]

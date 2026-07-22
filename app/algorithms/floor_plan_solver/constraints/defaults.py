from __future__ import annotations

from .hard import (
    AspectRatioConstraint,
    BoundaryPlacementConstraint,
    FrontAnchorConstraint,
    GaragePlacementConstraint,
    HallwayConnectivityConstraint,
    HallwayDimensionsConstraint,
    HardRoomRelationsConstraint,
    MinimumCoverageConstraint,
    RoomSizeHierarchyConstraint,
)
from .registry import ConstraintRegistry
from .soft import (
    BathroomDepthConstraint,
    CenterProximityConstraint,
    DeadSpaceConstraint,
    OptionalRoomPresenceConstraint,
    SeedStabilityConstraint,
    SoftRoomRelationsConstraint,
)


def build_default_registry() -> ConstraintRegistry:
    registry = ConstraintRegistry()

    registry.register_hard(AspectRatioConstraint())
    registry.register_hard(HardRoomRelationsConstraint())
    registry.register_hard(MinimumCoverageConstraint())
    registry.register_hard(HallwayConnectivityConstraint())
    registry.register_hard(HallwayDimensionsConstraint())
    registry.register_hard(FrontAnchorConstraint())
    registry.register_hard(GaragePlacementConstraint())
    registry.register_hard(BoundaryPlacementConstraint())
    registry.register_hard(RoomSizeHierarchyConstraint())

    registry.register_soft(SoftRoomRelationsConstraint())
    registry.register_soft(CenterProximityConstraint())
    registry.register_soft(DeadSpaceConstraint())
    registry.register_soft(SeedStabilityConstraint())
    registry.register_soft(BathroomDepthConstraint())
    registry.register_soft(OptionalRoomPresenceConstraint())

    return registry

"""
Type definitions organized by concern:
- Base primitives for geometry
- Domain models for core business logic
- Interface types for API contracts
- Solver-specific types in solvers/ subdirectory
- Constraint types from external models
"""

# Base geometry primitives
from .base import PointPayload, RoomBoundaryPayload, WallSegmentPayload

# Core domain models
from .domain import ConfigData, FpgRequirements, RoomData

# Opening and interior types
from .openings import (
    NormalizedRoom,
    OpeningPayload,
    OpeningRunResult,
    OpeningSide,
    RoomInput,
)

# API contract interfaces
from .interfaces import (
    CompactRoomPayload,
    DoorPayload,
    PostProcessInputPayload,
    PostProcessMetadataPayload,
    PostProcessOutputPayload,
    ProcessContextPayload,
    QuickPostProcessOutputPayload,
    RoomOutputPayload,
    RoomWallsPayload,
    VerandaMetadataPayload,
    WindowPayload,
    WallUnionResultPayload,
)

# Constraint types
from .room_relations_constraints import RoomRelationsConstraint

# Solver-specific types (lazy import)
from . import solvers

__all__ = [
    # Base primitives
    "PointPayload",
    "RoomBoundaryPayload",
    "WallSegmentPayload",
    # Domain models
    "RoomData",
    "ConfigData",
    "FpgRequirements",
    # Opening types
    "OpeningSide",
    "NormalizedRoom",
    "OpeningPayload",
    "OpeningRunResult",
    "RoomInput",
    # Interface contracts
    "ProcessContextPayload",
    "RoomWallsPayload",
    "WallUnionResultPayload",
    "CompactRoomPayload",
    "PostProcessInputPayload",
    "VerandaMetadataPayload",
    "PostProcessMetadataPayload",
    "RoomOutputPayload",
    "DoorPayload",
    "WindowPayload",
    "PostProcessOutputPayload",
    "QuickPostProcessOutputPayload",
    # Constraints
    "RoomRelationsConstraint",
    # Solvers (namespace)
    "solvers",
]

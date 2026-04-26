"""Solver-specific type definitions."""

from .constraints import (
    BackDoorCandidate,
    BackDoorDecisionVars,
    InternalDoorCandidate,
    InternalDoorDecisionVars,
    MainDoorCpSatVariables,
    ScaledRoomBounds,
    WindowCandidate,
    WindowDecisionVars,
)
from .graph import (
    GraphBoundary,
    GraphConvergence,
    GraphEdge,
    GraphLayoutResult,
    GraphNode,
    GraphPhysicsConfig,
    GraphScoreBreakdown,
)
from .optimization import FpgEvaluationResult, OptunaOptimizationResult

__all__ = [
    "GraphNode",
    "GraphEdge",
    "GraphBoundary",
    "GraphPhysicsConfig",
    "GraphConvergence",
    "GraphScoreBreakdown",
    "GraphLayoutResult",
    "ScaledRoomBounds",
    "MainDoorCpSatVariables",
    "InternalDoorCandidate",
    "InternalDoorDecisionVars",
    "WindowCandidate",
    "WindowDecisionVars",
    "BackDoorCandidate",
    "BackDoorDecisionVars",
    "FpgEvaluationResult",
    "OptunaOptimizationResult",
]

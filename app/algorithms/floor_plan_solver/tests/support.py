from __future__ import annotations

from dataclasses import dataclass

from app.algorithms.floor_plan_solver import FloorPlanSolveResult


@dataclass(frozen=True, slots=True)
class RefinementPipelineResults:
    initial: FloorPlanSolveResult
    refinement_a: FloorPlanSolveResult
    refinement_b: FloorPlanSolveResult

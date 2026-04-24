"""Soft constraint to encourage extender rooms to be larger.

Penalizes extender rooms that are undersized, encouraging them to use more space
when placement is feasible.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ortools.sat.python import cp_model

if TYPE_CHECKING:
    from app.algorithms.fpg_rooms.solver_models.room import Room


# Default penalty weight for undersized extenders
DEFAULT_EXTENDER_SIZE_PENALTY_WEIGHT = 10


def add_extender_placement_soft_penalty(
    model: cp_model.CpModel,
    rooms: list[Room],
    weight: int | None = None,
) -> cp_model.LinearExprT:
    """Create soft penalty for undersized extender rooms.
    
    Penalizes extender rooms that don't fully use their max width/height.
    This encourages the solver to expand extenders to their maximum when space permits.
    
    Args:
        model: CP-SAT solver model.
        rooms: List of all rooms (includes extender rooms).
        weight: Penalty weight per unit of underutilized space. Defaults to 10.
        
    Returns:
        LinearExprT representing the aggregated penalty cost (0 if all extenders maxed out).
    """
    if weight is None:
        weight = DEFAULT_EXTENDER_SIZE_PENALTY_WEIGHT
    
    penalty_terms: list[cp_model.LinearExprT] = []
    
    for room in rooms:
        # Check if this is an extender room by name pattern
        if not room.name.endswith("_ext"):
            continue
        
        # Skip if this extender has no max size defined
        if room.max_w == 0 or room.max_h == 0:
            continue
        
        # Penalty: sum of (max_w - actual_w) + (max_h - actual_h)
        # This incentivizes the solver to make w and h as close to max as possible
        if room.w is not None and room.h is not None:
            width_underutilization = room.max_w - room.w
            height_underutilization = room.max_h - room.h
            penalty_terms.append(
                cp_model.LinearExpr.Sum([
                    width_underutilization,
                    height_underutilization,
                ]) * weight
            )
    
    if not penalty_terms:
        return cp_model.LinearExpr.Sum([])
    
    return cp_model.LinearExpr.Sum(penalty_terms)

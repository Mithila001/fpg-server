"""Soft constraint for extender room sizing behavior.

Penalizes extenders only when they are active but below configured active minimums.
Inactive extenders (w=0, h=0) are not penalized.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ortools.sat.python import cp_model

from app.dev.dev_print import debug_log_data
from .extender_room_size import EXTENDER_ACTIVE_MIN_H, EXTENDER_ACTIVE_MIN_W

if TYPE_CHECKING:
    from app.algorithms.fpg_rooms.solver_models.room import Room


# Default penalty weight for undersized extenders
DEFAULT_EXTENDER_SIZE_PENALTY_WEIGHT = 10


def add_extender_placement_soft_penalty(
    model: Any,
    rooms: list[Room],
    weight: int | None = None,
) -> cp_model.LinearExprT:
    """Create soft penalty for active extenders that violate active minimums.

    This soft term is intentionally neutral for inactive extenders so optional
    extenders are not forced active by the objective.

    Args:
        model: CP-SAT solver model.
        rooms: List of all rooms (includes extender rooms).
        weight: Penalty weight per unit of underutilized space. Defaults to 10.

    Returns:
        LinearExprT representing the aggregated penalty cost.
    """

    if weight is None:
        weight = DEFAULT_EXTENDER_SIZE_PENALTY_WEIGHT

    penalty_terms: list[cp_model.LinearExprT] = []
    debug_log_data(
        f"add_extender_placement_soft_penalty: Adding extender placement soft penalty with weight {weight}",
        tag="EXTENDER_PLACEMENT_SOFT",
    )

    for room in rooms:
        # Check if this is an extender room by name pattern
        if not room.name.endswith("_ext"):
            continue

        # Skip if this extender has no max size defined
        if room.max_w == 0 or room.max_h == 0:
            debug_log_data(
                f"add_extender_placement_soft_penalty: Skipping extender room {room.name} with no max size defined.",
                tag="EXTENDER_PLACEMENT_SOFT",
            )
            continue

        if room.w is not None and room.h is not None:
            active_min_w = max(0, int(getattr(room, "min_w", 0)), EXTENDER_ACTIVE_MIN_W)
            active_min_h = max(0, int(getattr(room, "min_h", 0)), EXTENDER_ACTIVE_MIN_H)

            is_active = model.NewBoolVar(f"{room.name}_soft_is_active")
            model.Add(room.w >= 1).OnlyEnforceIf(is_active)
            model.Add(room.h >= 1).OnlyEnforceIf(is_active)
            model.Add(room.w == 0).OnlyEnforceIf(is_active.Not())
            model.Add(room.h == 0).OnlyEnforceIf(is_active.Not())

            width_shortfall = model.NewIntVar(
                0, active_min_w, f"{room.name}_soft_width_shortfall"
            )
            height_shortfall = model.NewIntVar(
                0, active_min_h, f"{room.name}_soft_height_shortfall"
            )
            model.Add(width_shortfall >= active_min_w - room.w)
            model.Add(height_shortfall >= active_min_h - room.h)

            active_shortfall = model.NewIntVar(
                0,
                active_min_w + active_min_h,
                f"{room.name}_soft_active_shortfall",
            )
            model.Add(active_shortfall == width_shortfall + height_shortfall)

            gated_shortfall = model.NewIntVar(
                0,
                active_min_w + active_min_h,
                f"{room.name}_soft_gated_shortfall",
            )
            model.Add(gated_shortfall == active_shortfall).OnlyEnforceIf(is_active)
            model.Add(gated_shortfall == 0).OnlyEnforceIf(is_active.Not())

            penalty_terms.append(cp_model.LinearExpr.Sum([gated_shortfall]) * weight)

    if not penalty_terms:
        return cp_model.LinearExpr.Sum([])

    return cp_model.LinearExpr.Sum(penalty_terms)

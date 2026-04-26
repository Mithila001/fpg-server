"""Hard constraint for optional extender room activation sizing.

Rules:
- If extender is active, enforce minimum width/height.
- If extender is inactive, force width/height to zero.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.algorithms.fpg_rooms.solver_models.room import Room


EXTENDER_ACTIVE_MIN_W = 10
EXTENDER_ACTIVE_MIN_H = 10


def add_extender_room_size_constraint(
    model: Any,
    rooms: list[Room],
    min_active_w: int = EXTENDER_ACTIVE_MIN_W,
    min_active_h: int = EXTENDER_ACTIVE_MIN_H,
) -> None:
    """Apply active/inactive size logic to extender rooms.

    Active  => w >= min_active_w and h >= min_active_h
    Inactive => w == 0 and h == 0
    """

    active_w = max(0, int(min_active_w))
    active_h = max(0, int(min_active_h))

    for room in rooms:
        if not room.is_extender:
            continue

        if room.w is None or room.h is None:
            continue

        is_active = model.NewBoolVar(f"{room.name}_is_active")

        model.Add(room.w >= active_w).OnlyEnforceIf(is_active)
        model.Add(room.h >= active_h).OnlyEnforceIf(is_active)

        model.Add(room.w == 0).OnlyEnforceIf(is_active.Not())
        model.Add(room.h == 0).OnlyEnforceIf(is_active.Not())

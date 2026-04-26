"""Hard constraints for garage side anchoring and frontage access.

Coordinate System Reference (see docs/COORDINATE_SYSTEM.md):
  - Front = y=0 (bottom of screen, street-facing)
  - Back  = y=max (top of screen, interior)
  - Left  = x=0 (viewer's left)
  - Right = x=max (viewer's right)

This module enforces garage placement so each garage:
  - Anchors near exactly one vertical floor boundary (left XOR right), and
  - Maintains vehicle access via direct front placement or full overlap with a
    verandaOutdoorSpace front wall segment.
"""

from __future__ import annotations

from typing import Any, List

from ortools.sat.python import cp_model

from app.core.fpg_rooms.config_fpg import GARAGE_SIDE_ANCHOR_THRESHOLD
from ...solver_models.room import Room


def add_garage_placement_constraints(
    model: Any,
    rooms: List[Room],
    floor_width: int,
    floor_height: int,
) -> None:
    """Apply refined hard garage placement rules.

    Hard Rules:
      1. Side anchoring (XOR):
         - Left anchored:  garage.x <= 20
         - Right anchored: garage.x_end >= (land_width - 20)
         Exactly one must hold.
      2. Vehicle access path (OR):
         - Garage front wall is on y=0, OR
         - Garage front wall fully overlaps at least one verandaOutdoorSpace
           horizontal wall segment (same y, full garage width covered).
    """
    solver_rooms = list(rooms)
    garages = [room for room in solver_rooms if room.type == "garage"]
    veranda_open_spaces = [room for room in rooms if room.type == "verandaOutdoorSpace"]

    if not garages:
        return

    # Use authoritative floor bounds from parent solver context.
    land_width = max(1, int(round(floor_width)))
    _land_height = max(1, int(round(floor_height)))

    # Apply constraints garage-by-garage (single-garage scenarios are the primary target).
    for garage in garages:
        assert garage.x is not None and garage.y is not None
        assert garage.x_end is not None and garage.y_end is not None

        # Side anchoring within 20 units of exactly one vertical floor boundary.
        garage_at_left = model.NewBoolVar(f"{garage.name}_at_left_side")  # type: ignore
        garage_at_right = model.NewBoolVar(f"{garage.name}_at_right_side")  # type: ignore

        model.Add(garage.x <= GARAGE_SIDE_ANCHOR_THRESHOLD).OnlyEnforceIf(
            garage_at_left
        )
        model.Add(garage.x > GARAGE_SIDE_ANCHOR_THRESHOLD).OnlyEnforceIf(
            garage_at_left.Not()
        )

        model.Add(
            garage.x_end >= land_width - GARAGE_SIDE_ANCHOR_THRESHOLD
        ).OnlyEnforceIf(garage_at_right)
        model.Add(
            garage.x_end < land_width - GARAGE_SIDE_ANCHOR_THRESHOLD
        ).OnlyEnforceIf(garage_at_right.Not())

        model.Add(garage_at_left + garage_at_right == 1)

        # Access path: y == 0 OR fully overlaps at least one verandaOutdoorSpace front wall.
        garage_front_on_boundary = model.NewBoolVar(f"{garage.name}_front_on_boundary")  # type: ignore
        model.Add(garage.y == 0).OnlyEnforceIf(garage_front_on_boundary)
        model.Add(garage.y > 0).OnlyEnforceIf(garage_front_on_boundary.Not())

        full_overlap_options: List[cp_model.IntVar] = [garage_front_on_boundary]

        for vos in veranda_open_spaces:
            assert vos.x is not None and vos.y is not None
            assert vos.x_end is not None and vos.y_end is not None

            overlap_with_vos = model.NewBoolVar(
                f"{garage.name}_front_fully_overlaps_{vos.name}"
            )  # type: ignore

            # Entire garage front segment [x, x_end] must lie on the same front wall segment.
            model.Add(vos.y == 0).OnlyEnforceIf(overlap_with_vos)
            model.Add(garage.y == vos.y).OnlyEnforceIf(overlap_with_vos)
            model.Add(garage.x >= vos.x).OnlyEnforceIf(overlap_with_vos)
            model.Add(garage.x_end <= vos.x_end).OnlyEnforceIf(overlap_with_vos)

            full_overlap_options.append(overlap_with_vos)

        model.AddBoolOr(full_overlap_options)

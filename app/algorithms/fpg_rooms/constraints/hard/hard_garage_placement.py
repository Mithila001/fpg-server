"""Hard constraints for garage positioning at front corners.

Coordinate System Reference (see docs/COORDINATE_SYSTEM.md):
  - Front = y=0 (bottom of screen, street-facing)
  - Back  = y=max (top of screen, interior)
  - Left  = x=0 (viewer's left)
  - Right = x=max (viewer's right)

This module enforces garage placement at the front boundary (y=0) with positioning
constraints to ensure garages are at front-left or front-right corners (not center).
"""

from __future__ import annotations

from typing import List

from ortools.sat.python import cp_model

from ...solver_models.room import Room


def add_garage_placement_constraints(
    model: cp_model.CpModel,
    rooms: List[Room],
) -> None:
    """Apply hard garage frontage and corner positioning rules.

    Hard Rules:
      1. Garage front wall is always on y=0 (front/street-facing, vehicle access).
      2. Garage must be positioned at front-left corner (x ≤ 10) 
         OR front-right corner (x_end ≥ land_width - 10).
      3. Garage cannot be positioned at both corners simultaneously (mutually exclusive).
    """
    real_rooms = [room for room in rooms if room.type != "verandaOutdoorSpace"]
    garages = [room for room in real_rooms if room.type == "garage"]

    if not garages:
        return

    # Keep bounds finite without relying on solver proto domains.
    land_width = max(30, sum(max(1, room.max_w) for room in real_rooms))

    # Constrain all garage rooms to the front (y=0) for street-facing access.
    for garage in garages:
        assert garage.x is not None and garage.y is not None
        assert garage.x_end is not None and garage.y_end is not None

        # Front wall of garage is always on y=0 (street-facing, vehicle access).
        # y=0 is the minimum y value, anchoring garage at the front boundary.
        model.Add(garage.y == 0)

        # Garage must be positioned at front-left corner or front-right corner (not center).
        # Create two boolean variables: one for each corner option.
        garage_at_left = model.NewBoolVar(f"{garage.name}_at_left_corner")  # type: ignore
        garage_at_right = model.NewBoolVar(f"{garage.name}_at_right_corner")  # type: ignore

        # Define what each condition means with bidirectional constraints.
        # Left: garage.x near 0 (within first 10 units)
        model.Add(garage.x <= 10).OnlyEnforceIf(garage_at_left)
        model.Add(garage.x > 10).OnlyEnforceIf(garage_at_left.Not())

        # Right: garage.x_end near land_width (within last 10 units)
        model.Add(garage.x_end >= land_width - 10).OnlyEnforceIf(garage_at_right)
        model.Add(garage.x_end < land_width - 10).OnlyEnforceIf(garage_at_right.Not())

        # Force EXACTLY one corner (mutually exclusive: left XOR right)
        # This means: (left AND NOT right) OR (NOT left AND right)
        model.AddBoolOr([garage_at_left, garage_at_right])  # At least one
        model.Add(garage_at_left + garage_at_right == 1)    # Exactly one

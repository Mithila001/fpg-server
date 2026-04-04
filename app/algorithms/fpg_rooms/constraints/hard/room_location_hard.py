"""Room location constraints to establish anchor room positioning.

Coordinate System Reference (see docs/COORDINATE_SYSTEM.md):
  - Front (entrance) = y=0 (minimum y)
  - Back (interior)  = y=max (maximum y)
  - Left = x=0 (minimum x)
  - Right = x=max (maximum x)

When veranda is present, it anchors at front (y≈0). Without veranda,
livingRoom serves as the anchor toward the back.
"""

from typing import List

from ortools.sat.python import cp_model

from ...solver_models.room import Room


def add_living_room_bottom_most_constraint(
    model: cp_model.CpModel,
    rooms: List[Room],
) -> None:
    """Enforce anchor room positioning based on frontage requirements.

    Coordinate System (see docs/COORDINATE_SYSTEM.md):
      - Front (y=0): Street-facing, entrance side.
      - Back (y=max): Interior side.

    With veranda present:
      - Veranda is front-anchored at y=0 via open-area placement.
      - Center-y constraint: veranda.center_y <= all_other_rooms.center_y
      - Result: Veranda stays nearest to front; other rooms extend deeper (toward back).

    Without veranda (fallback):
      - LivingRoom serves as interior anchor.
      - Center-y constraint: living_room.center_y >= all_other_rooms.center_y
      - Result: Legacy behavior where living room is positioned toward back.
      - Prevents broad regressions in non-veranda layouts.
    """
    veranda_rooms = [room for room in rooms if room.type == "veranda"]
    if veranda_rooms:
        bottom_room = veranda_rooms[0]
        anchor_is_veranda = True
    else:
        living_rooms = [room for room in rooms if room.type == "livingRoom"]
        if not living_rooms:
            return
        bottom_room = living_rooms[0]
        anchor_is_veranda = False

    for room in rooms:
        if room is bottom_room:
            continue
        if anchor_is_veranda:
            model.Add(bottom_room.y + bottom_room.y_end <= room.y + room.y_end)  # type: ignore
        else:
            model.Add(bottom_room.y + bottom_room.y_end >= room.y + room.y_end)  # type: ignore

"""
Hallway constraints for the floor plan generator.

Activated only when at least one room with ``type == "Hallway"`` is present in
the rooms list.  If no hallways are requested the function returns immediately
so existing layouts are completely unaffected.

Rules enforced per hallway
--------------------------
1. Fixed-width / scalable-length shape
   Each hallway has a fixed narrow dimension (HALLWAY_WIDTH) and a freely
   scalable long dimension (>= HALLWAY_MIN_LENGTH).  A per-hallway orientation
   BoolVar ``is_horizontal`` decides which axis carries which role.

2. Living-room connection (hard)
   Every hallway must share a touching edge with the living room.

3. At-least-one extra room connection (hard via OR)
   Every hallway must also touch at least one non-hallway, non-living-room
   room, making it a practical routing path between that room and the living
   room.

Usage
-----
The Hallway room should be included in FpgRequirements with dimensions that
allow both orientations, for example:
    RoomData("Hallway", "Hallway", min_w=HALLWAY_WIDTH, min_h=HALLWAY_WIDTH,
             max_w=floor_w, max_h=floor_h)
The constraints here will then further restrict the actual width/height to the
fixed-narrow + scalable-long shape according to the chosen orientation.
"""

from ortools.sat.python import cp_model
from typing import List

from ..solver_models.room import Room
from ..config import HALLWAY_WIDTH, HALLWAY_MIN_LENGTH

# Minimum shared-edge length required for a hallway ↔ room connection.
# Set to HALLWAY_WIDTH so the requirement is always satisfiable even when the
# hallway touches a room on its narrow face.
_MIN_OVERLAP = HALLWAY_WIDTH


def _touch_constraints(
    model: cp_model.CpModel,
    room1: Room,
    room2: Room,
    enforcer=None,
) -> None:
    """Add touch constraints between room1 and room2.

    When *enforcer* is None the pair must always share an edge (hard
    constraint).  When supplied, the pair is only required to touch when the
    enforcer BoolVar is True.

    A minimum shared-edge overlap of _MIN_OVERLAP is enforced so adjacency is
    meaningful (not just a corner).
    """
    suffix = f"{room1.name}_{room2.name}"

    touch_right = model.NewBoolVar(f"h_tr_{suffix}")  # type: ignore
    touch_left = model.NewBoolVar(f"h_tl_{suffix}")  # type: ignore
    touch_top = model.NewBoolVar(f"h_tt_{suffix}")  # type: ignore
    touch_bottom = model.NewBoolVar(f"h_tb_{suffix}")  # type: ignore

    conds: list = [] if enforcer is None else [enforcer]

    # ── Channelling: BoolVar is True iff the corresponding face equality holds ─
    model.Add(room1.x == room2.x_end).OnlyEnforceIf(conds + [touch_right])  # type: ignore
    model.Add(room1.x_end == room2.x).OnlyEnforceIf(conds + [touch_left])  # type: ignore
    model.Add(room1.y == room2.y_end).OnlyEnforceIf(conds + [touch_top])  # type: ignore
    model.Add(room1.y_end == room2.y).OnlyEnforceIf(conds + [touch_bottom])  # type: ignore

    # ── At least one direction must be active ─────────────────────────────────
    all_touch = [touch_right, touch_left, touch_top, touch_bottom]
    if enforcer is None:
        model.AddBoolOr(all_touch)  # type: ignore
    else:
        model.AddBoolOr(all_touch).OnlyEnforceIf(enforcer)  # type: ignore

    # ── Minimum shared-edge overlap ───────────────────────────────────────────
    # Vertical face touches (right/left) → y-extents must overlap
    for t in (touch_right, touch_left):
        model.Add(room1.y + _MIN_OVERLAP <= room2.y_end).OnlyEnforceIf(conds + [t])  # type: ignore
        model.Add(room2.y + _MIN_OVERLAP <= room1.y_end).OnlyEnforceIf(conds + [t])  # type: ignore

    # Horizontal face touches (top/bottom) → x-extents must overlap
    for t in (touch_top, touch_bottom):
        model.Add(room1.x + _MIN_OVERLAP <= room2.x_end).OnlyEnforceIf(conds + [t])  # type: ignore
        model.Add(room2.x + _MIN_OVERLAP <= room1.x_end).OnlyEnforceIf(conds + [t])  # type: ignore


def add_hallway_constraints(
    model: cp_model.CpModel,
    rooms: List[Room],
    floor_w: int,
    floor_h: int,
    hallway_used: cp_model.IntVar | None = None,
) -> None:
    """Apply all hallway-specific constraints.

    Safe to call unconditionally — returns immediately when no hallways are
    present, ensuring zero impact on layouts that don't use hallways.
    """
    hallways = [r for r in rooms if r.type == "hallway"]
    if not hallways:
        return

    non_hallways = [r for r in rooms if r.type != "hallway"]
    living_rooms = [r for r in non_hallways if r.type == "livingRoom"]
    extra_rooms = [r for r in non_hallways if r.type != "livingRoom"]

    # Safety guard from business rules: if multiple living rooms appear,
    # only the first one is used for hallway connectivity constraints.
    living_room = living_rooms[0] if living_rooms else None

    if hallway_used is None:
        hallway_used = model.NewBoolVar("hallway_used_default")  # type: ignore
        model.Add(hallway_used == 1)  # type: ignore

    for hallway in hallways:
        assert hallway.w is not None and hallway.h is not None

        # Hallway can be disabled entirely when not selected by the solver.
        model.Add(hallway.w == 0).OnlyEnforceIf(hallway_used.Not())  # type: ignore
        model.Add(hallway.h == 0).OnlyEnforceIf(hallway_used.Not())  # type: ignore

        # ── Rule 1: Fixed-width / scalable-length shape ───────────────────────
        is_horizontal = model.NewBoolVar(f"{hallway.name}_is_horizontal")  # type: ignore

        # Horizontal: w is the long, free side; h is the fixed narrow side
        model.Add(hallway.w >= HALLWAY_MIN_LENGTH).OnlyEnforceIf(  # type: ignore[attr-defined]
            [hallway_used, is_horizontal]
        )
        model.Add(hallway.h == HALLWAY_WIDTH).OnlyEnforceIf(  # type: ignore[attr-defined]
            [hallway_used, is_horizontal]
        )

        # Vertical: h is the long, free side; w is the fixed narrow side
        model.Add(hallway.h >= HALLWAY_MIN_LENGTH).OnlyEnforceIf(  # type: ignore[attr-defined]
            [hallway_used, is_horizontal.Not()]
        )
        model.Add(hallway.w == HALLWAY_WIDTH).OnlyEnforceIf(  # type: ignore[attr-defined]
            [hallway_used, is_horizontal.Not()]
        )

        # ── Rule 2: Living-room connection (hard) ─────────────────────────────
        if living_room is not None:
            # Hard when hallway is active: hallway must touch living room.
            _touch_constraints(model, hallway, living_room, enforcer=hallway_used)

        # ── Rule 3: At-least-one extra room connection ────────────────────────
        if extra_rooms:
            extra_adj_vars = []
            for other in extra_rooms:
                is_adj = model.NewBoolVar(  # type: ignore
                    f"{hallway.name}_extra_adj_{other.name}"
                )
                extra_adj_vars.append(is_adj)
                _touch_constraints(model, hallway, other, enforcer=is_adj)
                model.AddImplication(is_adj, hallway_used)  # type: ignore[attr-defined]
            model.AddBoolOr(extra_adj_vars).OnlyEnforceIf(hallway_used)  # type: ignore

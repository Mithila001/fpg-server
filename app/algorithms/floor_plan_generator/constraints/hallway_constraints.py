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

4. Bounding-box containment
   A hallway may not extend beyond the combined axis-aligned bounding box of
   all non-hallway rooms — it cannot "pop out of the outer walls".

5. Hallway-to-hallway joining (when > 1 hallway)
   If two hallways share a touching face, their face-segment coordinates must
   be fully aligned (no staggered joins).

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
    model.Add(room1.x != room2.x_end).OnlyEnforceIf(conds + [touch_right.Not()])  # type: ignore

    model.Add(room1.x_end == room2.x).OnlyEnforceIf(conds + [touch_left])  # type: ignore
    model.Add(room1.x_end != room2.x).OnlyEnforceIf(conds + [touch_left.Not()])  # type: ignore

    model.Add(room1.y == room2.y_end).OnlyEnforceIf(conds + [touch_top])  # type: ignore
    model.Add(room1.y != room2.y_end).OnlyEnforceIf(conds + [touch_top.Not()])  # type: ignore

    model.Add(room1.y_end == room2.y).OnlyEnforceIf(conds + [touch_bottom])  # type: ignore
    model.Add(room1.y_end != room2.y).OnlyEnforceIf(conds + [touch_bottom.Not()])  # type: ignore

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
) -> None:
    """Apply all hallway-specific constraints.

    Safe to call unconditionally — returns immediately when no hallways are
    present, ensuring zero impact on layouts that don't use hallways.
    """
    hallways = [r for r in rooms if r.type == "Hallway"]
    if not hallways:
        return

    non_hallways = [r for r in rooms if r.type != "Hallway"]
    living_rooms = [r for r in non_hallways if r.type == "LivingRoom"]
    extra_rooms = [r for r in non_hallways if r.type != "LivingRoom"]

    # ── Bounding-box auxiliary variables ──────────────────────────────────────
    # Derived from all non-hallway rooms so hallways cannot exceed the outer
    # envelope of the house.
    if non_hallways:
        bb_x_min = model.NewIntVar(0, floor_w, "hallway_bb_x_min")  # type: ignore
        bb_x_max = model.NewIntVar(0, floor_w, "hallway_bb_x_max")  # type: ignore
        bb_y_min = model.NewIntVar(0, floor_h, "hallway_bb_y_min")  # type: ignore
        bb_y_max = model.NewIntVar(0, floor_h, "hallway_bb_y_max")  # type: ignore

        model.AddMinEquality(bb_x_min, [r.x for r in non_hallways])  # type: ignore
        model.AddMaxEquality(bb_x_max, [r.x_end for r in non_hallways])  # type: ignore
        model.AddMinEquality(bb_y_min, [r.y for r in non_hallways])  # type: ignore
        model.AddMaxEquality(bb_y_max, [r.y_end for r in non_hallways])  # type: ignore

    for hallway in hallways:
        # ── Rule 1: Fixed-width / scalable-length shape ───────────────────────
        is_horizontal = model.NewBoolVar(f"{hallway.name}_is_horizontal")  # type: ignore

        # Horizontal: w is the long, free side; h is the fixed narrow side
        model.Add(hallway.w >= HALLWAY_MIN_LENGTH).OnlyEnforceIf(is_horizontal)  # type: ignore
        model.Add(hallway.h == HALLWAY_WIDTH).OnlyEnforceIf(is_horizontal)  # type: ignore

        # Vertical: h is the long, free side; w is the fixed narrow side
        model.Add(hallway.h >= HALLWAY_MIN_LENGTH).OnlyEnforceIf(is_horizontal.Not())  # type: ignore
        model.Add(hallway.w == HALLWAY_WIDTH).OnlyEnforceIf(is_horizontal.Not())  # type: ignore

        # ── Rule 2: Living-room connection (hard) ─────────────────────────────
        if living_rooms:
            if len(living_rooms) == 1:
                # Hard: hallway must always touch the living room
                _touch_constraints(model, hallway, living_rooms[0], enforcer=None)
            else:
                lr_adj_vars = []
                for lr in living_rooms:
                    is_adj = model.NewBoolVar(  # type: ignore
                        f"{hallway.name}_lr_adj_{lr.name}"
                    )
                    lr_adj_vars.append(is_adj)
                    _touch_constraints(model, hallway, lr, enforcer=is_adj)
                model.AddBoolOr(lr_adj_vars)  # type: ignore

        # ── Rule 3: At-least-one extra room connection ────────────────────────
        if extra_rooms:
            extra_adj_vars = []
            for other in extra_rooms:
                is_adj = model.NewBoolVar(  # type: ignore
                    f"{hallway.name}_extra_adj_{other.name}"
                )
                extra_adj_vars.append(is_adj)
                _touch_constraints(model, hallway, other, enforcer=is_adj)
            model.AddBoolOr(extra_adj_vars)  # type: ignore

        # ── Rule 4: Bounding-box containment ──────────────────────────────────
        if non_hallways:
            model.Add(hallway.x >= bb_x_min)  # type: ignore
            model.Add(hallway.x_end <= bb_x_max)  # type: ignore
            model.Add(hallway.y >= bb_y_min)  # type: ignore
            model.Add(hallway.y_end <= bb_y_max)  # type: ignore

    # ── Rule 5: Hallway-to-hallway full-edge alignment ────────────────────────
    # Only applies when more than one hallway exists.  If two hallways touch,
    # their shared face segment must be perfectly aligned (no staggered joins).
    for i in range(len(hallways)):
        for j in range(i + 1, len(hallways)):
            h1 = hallways[i]
            h2 = hallways[j]
            suffix = f"{h1.name}_{h2.name}"

            hh_tr = model.NewBoolVar(f"hh_tr_{suffix}")  # type: ignore
            hh_tl = model.NewBoolVar(f"hh_tl_{suffix}")  # type: ignore
            hh_tt = model.NewBoolVar(f"hh_tt_{suffix}")  # type: ignore
            hh_tb = model.NewBoolVar(f"hh_tb_{suffix}")  # type: ignore

            # Channelling: BoolVar tracks whether the face equality holds
            model.Add(h1.x == h2.x_end).OnlyEnforceIf(hh_tr)  # type: ignore
            model.Add(h1.x != h2.x_end).OnlyEnforceIf(hh_tr.Not())  # type: ignore
            model.Add(h1.x_end == h2.x).OnlyEnforceIf(hh_tl)  # type: ignore
            model.Add(h1.x_end != h2.x).OnlyEnforceIf(hh_tl.Not())  # type: ignore
            model.Add(h1.y == h2.y_end).OnlyEnforceIf(hh_tt)  # type: ignore
            model.Add(h1.y != h2.y_end).OnlyEnforceIf(hh_tt.Not())  # type: ignore
            model.Add(h1.y_end == h2.y).OnlyEnforceIf(hh_tb)  # type: ignore
            model.Add(h1.y_end != h2.y).OnlyEnforceIf(hh_tb.Not())  # type: ignore

            # Full-edge alignment when touching on a vertical face (right/left):
            # both hallways must share exactly the same y-extent.
            for t in (hh_tr, hh_tl):
                model.Add(h1.y == h2.y).OnlyEnforceIf(t)  # type: ignore
                model.Add(h1.y_end == h2.y_end).OnlyEnforceIf(t)  # type: ignore

            # Full-edge alignment when touching on a horizontal face (top/bottom):
            # both hallways must share exactly the same x-extent.
            for t in (hh_tt, hh_tb):
                model.Add(h1.x == h2.x).OnlyEnforceIf(t)  # type: ignore
                model.Add(h1.x_end == h2.x_end).OnlyEnforceIf(t)  # type: ignore

"""
Hallway constraints for the floor plan generator.
"""

from ortools.sat.python import cp_model
from typing import List, Dict, Any

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
) -> Dict[str, Any]:
    """Apply hallway-specific constraints and return activation metadata.

    Creates per-hallway activation BoolVars internally and enforces geometry
    rules (fixed-width/scalable-length, living-room connection, and at least
    one additional non-living-room connection) for each active hallway.
    Allows solver to activate 0, 1, or 2 hallways.

    Args:
        model: CP-SAT model to add constraints to.
        rooms: List of all rooms including hallway rooms.

    Returns:
        Dict with keys:
        - 'hallway_activation': dict mapping hallway room names to their BoolVar
        - 'hallway_usage_sum': LinearExpr summing all active hallways (for objective)
        - 'hallway_rooms': list of hallway room objects processed

        Returns empty dict if no hallways are present.
    """
    hallways = [r for r in rooms if r.type == "hallway"]
    if not hallways:
        return {}

    non_hallways = [r for r in rooms if r.type != "hallway"]
    
    living_rooms = [r for r in non_hallways if r.type == "livingRoom"]
    living_room = living_rooms[0] if living_rooms else None
    
    non_living_rooms = [r for r in non_hallways if r.type != "livingRoom"]

    hallway_activation: Dict[str, cp_model.IntVar] = {}
    activation_list: List[cp_model.IntVar] = []

    for hallway in hallways:
        assert hallway.w is not None and hallway.h is not None

        # Create per-hallway activation BoolVar
        is_active = model.NewBoolVar(f"{hallway.name}_active")  # type: ignore
        hallway_activation[hallway.name] = is_active
        activation_list.append(is_active)

        # Hallway can be disabled entirely when not active.
        model.Add(hallway.w == 0).OnlyEnforceIf(is_active.Not())  # type: ignore
        model.Add(hallway.h == 0).OnlyEnforceIf(is_active.Not())  # type: ignore

        # ── Rule 1: Fixed-width / scalable-length shape ───────────────────────
        is_horizontal = model.NewBoolVar(f"{hallway.name}_is_horizontal")  # type: ignore

        # Horizontal: w is the long, free side; h is the fixed narrow side
        model.Add(hallway.w >= HALLWAY_MIN_LENGTH).OnlyEnforceIf(  # type: ignore[attr-defined]
            [is_active, is_horizontal]
        )
        model.Add(hallway.h == HALLWAY_WIDTH).OnlyEnforceIf(  # type: ignore[attr-defined]
            [is_active, is_horizontal]
        )

        # Vertical: h is the long, free side; w is the fixed narrow side
        model.Add(hallway.h >= HALLWAY_MIN_LENGTH).OnlyEnforceIf(  # type: ignore[attr-defined]
            [is_active, is_horizontal.Not()]
        )
        model.Add(hallway.w == HALLWAY_WIDTH).OnlyEnforceIf(  # type: ignore[attr-defined]
            [is_active, is_horizontal.Not()]
        )

        # ── Rule 2: Living-room connection (hard when active) ─────────────────
        if living_room is not None:
            _touch_constraints(model, hallway, living_room, enforcer=is_active)
        else:
            # No living room available means hallway cannot be activated.
            model.Add(is_active == 0)

        # ── Rule 3: Must touch at least one non-living room when active ──────
        if non_living_rooms:
            touches_non_living: List[cp_model.IntVar] = []
            for room in non_living_rooms:
                touches_room = model.NewBoolVar(
                    f"{hallway.name}_touch_non_living_{room.name}"
                )  # type: ignore
                touches_non_living.append(touches_room)

                _touch_constraints(model, hallway, room, enforcer=touches_room)
                model.AddImplication(touches_room, is_active)  # type: ignore

            model.AddBoolOr(touches_non_living).OnlyEnforceIf(is_active)  # type: ignore
        else:
            # No non-living room available means hallway cannot be activated.
            model.Add(is_active == 0)

    # ── Cardinality: at most 2 hallways active ────────────────────────────────
    model.Add(cp_model.LinearExpr.Sum(activation_list) <= 2)  # type: ignore

    # Return metadata for parent to use in objective and adjacency
    hallway_usage_sum = cp_model.LinearExpr.Sum(activation_list)
    return {
        "hallway_activation": hallway_activation,
        "hallway_usage_sum": hallway_usage_sum,
        "hallway_rooms": hallways,
    }

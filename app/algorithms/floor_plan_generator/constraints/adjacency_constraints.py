from ortools.sat.python import cp_model
from typing import Any, List

from ..solver_models.room import Room
from app.schemas.db.room_relations_constraints import RoomRelationsConstraintBase


def _conditional_constraint(
    model: cp_model.CpModel,
    room1: Room,
    room2: Room,
    enforcer: Any | None = None,
) -> None:
    """Require two rooms to share an edge when active."""

    suffix = f"{room1.name}_{room2.name}"

    touch_right = model.NewBoolVar(f"touch_right_{suffix}")  # type: ignore
    touch_left = model.NewBoolVar(f"touch_left_{suffix}")  # type: ignore
    touch_top = model.NewBoolVar(f"touch_top_{suffix}")  # type: ignore
    touch_bottom = model.NewBoolVar(f"touch_bottom_{suffix}")  # type: ignore

    conds: List[Any] = []
    if enforcer is not None:
        conds.append(enforcer)

    model.Add(room1.x == room2.x_end).OnlyEnforceIf(conds + [touch_right])  # type: ignore
    model.Add(room1.x != room2.x_end).OnlyEnforceIf(conds + [touch_right.Not()])  # type: ignore

    model.Add(room1.x_end == room2.x).OnlyEnforceIf(conds + [touch_left])  # type: ignore
    model.Add(room1.x_end != room2.x).OnlyEnforceIf(conds + [touch_left.Not()])  # type: ignore

    model.Add(room1.y == room2.y_end).OnlyEnforceIf(conds + [touch_top])  # type: ignore
    model.Add(room1.y != room2.y_end).OnlyEnforceIf(conds + [touch_top.Not()])  # type: ignore

    model.Add(room1.y_end == room2.y).OnlyEnforceIf(conds + [touch_bottom])  # type: ignore
    model.Add(room1.y_end != room2.y).OnlyEnforceIf(conds + [touch_bottom.Not()])  # type: ignore

    if enforcer is not None:
        model.AddBoolOr(  # type: ignore
            [touch_right, touch_left, touch_top, touch_bottom]
        ).OnlyEnforceIf(enforcer)  # type: ignore[attr-defined]
    else:
        model.AddBoolOr([touch_right, touch_left, touch_top, touch_bottom])  # type: ignore[attr-defined]

    MIN_OVERLAP = 10

    # Vertical-face touches (left/right) require overlap on y-axis.
    for t in (touch_right, touch_left):
        model.Add(room1.y + MIN_OVERLAP <= room2.y_end).OnlyEnforceIf(conds + [t])  # type: ignore
        model.Add(room2.y + MIN_OVERLAP <= room1.y_end).OnlyEnforceIf(conds + [t])  # type: ignore

    # Horizontal-face touches (top/bottom) require overlap on x-axis.
    for t in (touch_top, touch_bottom):
        model.Add(room1.x + MIN_OVERLAP <= room2.x_end).OnlyEnforceIf(conds + [t])  # type: ignore
        model.Add(room2.x + MIN_OVERLAP <= room1.x_end).OnlyEnforceIf(conds + [t])  # type: ignore


def adjacency_constraints(
    model: cp_model.CpModel,
    rooms_list: List[Room],
    relations: List[RoomRelationsConstraintBase],
) -> List[cp_model.IntVar]:
    """Convert database adjacency rules into CP-SAT constraints.

    Applies relation rules uniformly to all room types, treating hallways as
    a normal room type. Hallway activation is handled by hallway_constraints;
    this module simply applies the rules defined in the database relations.
    """

    ### IMPORTANT : In this function, we apply rules uniformly per room type.
    living_touch_vars: List[cp_model.IntVar] = []
    living_touch_by_room: dict[str, cp_model.IntVar] = {}

    for rec in relations:
        related_types = (
            rec.related_room or []
        )  # Relationship Room list for specific Room Type
        if not related_types:
            continue

        subject_rooms = [
            r for r in rooms_list if r.type == rec.room_type
        ]  # Origin Rooms list
        if not subject_rooms:
            continue

        candidates = [
            r for r in rooms_list if r.type in related_types
        ]  # Neighbor Rooms list
        if not candidates:
            continue

        # For each Origin Room:
        for room1 in subject_rooms:
            if len(candidates) == 1:
                # Only one neighbor type available—must touch it
                _conditional_constraint(model, room1, candidates[0], enforcer=None)
                continue

            # Multiple neighbor types—must touch at least one
            adj_switches: List[Any] = []
            for room2 in candidates:
                if room1.name == room2.name:
                    continue

                is_adj = model.NewBoolVar(f"is_adj_{room1.name}_{room2.name}")  # type: ignore
                adj_switches.append(is_adj)
                _conditional_constraint(model, room1, room2, enforcer=is_adj)

            if adj_switches:
                model.AddBoolOr(adj_switches)  # type: ignore

            # Track living-room touch for objective penalty
            if "livingRoom" in related_types:
                has_living_touch = living_touch_by_room.get(room1.name)
                if has_living_touch is None:
                    has_living_touch = model.NewBoolVar(  # type: ignore
                        f"has_living_touch_{room1.name}"
                    )
                    living_touch_by_room[room1.name] = has_living_touch
                    living_touch_vars.append(has_living_touch)

                living_candidates = [r for r in candidates if r.type == "livingRoom"]
                if living_candidates:
                    living_candidate = living_candidates[0]
                    if room1.name != living_candidate.name:
                        is_living_adj = model.NewBoolVar(  # type: ignore
                            f"is_adj_{room1.name}_{living_candidate.name}"
                        )
                        _conditional_constraint(
                            model, room1, living_candidate, enforcer=is_living_adj
                        )
                        model.Add(has_living_touch == is_living_adj)  # type: ignore
                    else:
                        model.Add(has_living_touch == 0)  # type: ignore
                else:
                    model.Add(has_living_touch == 0)  # type: ignore

    return living_touch_vars

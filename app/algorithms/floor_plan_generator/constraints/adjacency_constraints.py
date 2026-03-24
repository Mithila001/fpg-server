from ortools.sat.python import cp_model
from typing import Any, List, Optional

from ..solver_models.room import Room
from app.schemas.db.room_relations_constraints import RoomRelationsConstraintBase


def _conditional_constraint(
    model: cp_model.CpModel,
    room1: Room,
    room2: Room,
    enforcer: Any | None = None,
    min_overlap: int = 1,
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

    # Vertical-face touches (left/right) require overlap on y-axis.
    for t in (touch_right, touch_left):
        model.Add(room1.y + min_overlap <= room2.y_end).OnlyEnforceIf(conds + [t])  # type: ignore
        model.Add(room2.y + min_overlap <= room1.y_end).OnlyEnforceIf(conds + [t])  # type: ignore

    # Horizontal-face touches (top/bottom) require overlap on x-axis.
    for t in (touch_top, touch_bottom):
        model.Add(room1.x + min_overlap <= room2.x_end).OnlyEnforceIf(conds + [t])  # type: ignore
        model.Add(room2.x + min_overlap <= room1.x_end).OnlyEnforceIf(conds + [t])  # type: ignore


def _hard_adjacency_constraints(
    model: cp_model.CpModel,
    rooms_list: List[Room],
    hardRelations: List[RoomRelationsConstraintBase],
    min_overlap: int = 1,
) -> None:
    """Apply hard adjacency relations as mandatory per-required-type connections.
    
    Each required_type in the rule must be satisfied independently:
    room must touch at least one candidate of EACH listed type (AND across types).
    Within each type, at least one candidate suffices (OR within type).
    """

    for room in rooms_list:
        matching_rules = [rel for rel in hardRelations if rel.room_type == room.type]
        if not matching_rules:
            continue

        for rule in matching_rules:
            related_types = rule.related_room or []
            if not related_types:
                continue

            print(f"[adjacency] Room '{room.name}' (type={room.type}) requires one of each type in {related_types}")

            # For each required type, this room must touch at least one
            # candidate room of that type (satisfied independently).
            for required_type in related_types:
                candidates = [
                    r
                    for r in rooms_list
                    if r.type == required_type and r.name != room.name
                ]
                if not candidates:
                    print(
                        f"[adjacency]  - no candidates for required type '{required_type}' for room '{room.name}'"
                    )
                    # No candidates means infeasible for this required_type
                    model.AddBoolOr([])
                    continue

                print(
                    f"[adjacency]  - required_type '{required_type}' candidates: {[c.name for c in candidates]}"
                )

                adj_switches: List[Any] = []
                for candidate in candidates:
                    is_adj = model.NewBoolVar(f"is_adj_{room.name}_{candidate.name}")  # type: ignore
                    adj_switches.append(is_adj)
                    print(
                        f"[adjacency]    - adding conditional adjacency bool var '{is_adj.Name()}' for '{room.name}' <-> '{candidate.name}'"
                    )
                    _conditional_constraint(
                        model,
                        room,
                        candidate,
                        enforcer=is_adj,
                        min_overlap=min_overlap,
                    )

                model.AddBoolOr(adj_switches)  # type: ignore
                print(
                    f"[adjacency]    - added OR of {[v.Name() for v in adj_switches]} for required_type '{required_type}'"
                )


def adjacency_constraints(
    model: cp_model.CpModel,
    rooms_list: List[Room],
    hardRelations: Optional[List[RoomRelationsConstraintBase]] = None,
    softRelations: Optional[List[RoomRelationsConstraintBase]] = None,
    min_overlap: int = 1,
) -> List[cp_model.IntVar]:
    """Apply adjacency constraints.

    Returns an empty list when hard or soft relations are missing/invalid.
    For now, only hard relations are enforced.
    """

    if not isinstance(hardRelations, list) or not hardRelations:
        return []

    if not isinstance(softRelations, list) or not softRelations:
        return []

    _hard_adjacency_constraints(model, rooms_list, hardRelations, min_overlap=min_overlap)

    return []

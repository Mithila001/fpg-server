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


def hard_AND_adjacency_constraints(
    model: cp_model.CpModel,
    rooms_list: List[Room],
    hard_AND_Relations: List[RoomRelationsConstraintBase],
    min_overlap: int = 1,
) -> None:
    """Apply hard AND adjacency relations: room MUST touch ALL listed types.
    
    Each required_type in the rule must be satisfied independently:
    room must touch at least one candidate of EACH listed type (AND across types).
    Within each type, at least one candidate suffices (OR within type).
    """

    for room in rooms_list:
        matching_rules = [rel for rel in hard_AND_Relations if rel.room_type == room.type]
        if not matching_rules:
            continue

        for rule in matching_rules:
            related_types = rule.related_room or []
            if not related_types:
                continue

            print(f"[adjacency|hard_AND] Room '{room.name}' (type={room.type}) requires one of each type in {related_types}")

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
                        f"[adjacency|hard_AND]  - no candidates for required type '{required_type}' for room '{room.name}'"
                    )
                    # No candidates means infeasible for this required_type
                    model.AddBoolOr([])
                    continue

                print(
                    f"[adjacency|hard_AND]  - required_type '{required_type}' candidates: {[c.name for c in candidates]}"
                )

                adj_switches: List[Any] = []
                for candidate in candidates:
                    is_adj = model.NewBoolVar(f"is_adj_{room.name}_{candidate.name}")  # type: ignore
                    adj_switches.append(is_adj)
                    print(
                        f"[adjacency|hard_AND]    - adding conditional adjacency bool var '{is_adj.Name()}' for '{room.name}' <-> '{candidate.name}'"
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
                    f"[adjacency|hard_AND]    - added OR of {[v.Name() for v in adj_switches]} for required_type '{required_type}'"
                )


def hard_OR_adjacency_constraints(
    model: cp_model.CpModel,
    rooms_list: List[Room],
    hard_OR_Relations: List[RoomRelationsConstraintBase],
    min_overlap: int = 1,
) -> None:
    """Apply hard OR adjacency relations: room MUST touch AT LEAST ONE of the listed types.
    
    The room must satisfy at least one type from the related_types list (OR across types).
    Within all candidate rooms of all types, at least one adjacency must be satisfied.
    """

    for room in rooms_list:
        matching_rules = [rel for rel in hard_OR_Relations if rel.room_type == room.type]
        if not matching_rules:
            continue

        for rule in matching_rules:
            related_types = rule.related_room or []
            if not related_types:
                continue

            print(f"[adjacency|hard_OR] Room '{room.name}' (type={room.type}) requires at least one of types in {related_types}")

            # Collect all candidates across all types
            all_candidates: List[Room] = []
            for required_type in related_types:
                candidates = [
                    r
                    for r in rooms_list
                    if r.type == required_type and r.name != room.name
                ]
                all_candidates.extend(candidates)

            if not all_candidates:
                print(
                    f"[adjacency|hard_OR]  - no candidates across types {related_types} for room '{room.name}'"
                )
                # No candidates means infeasible for this rule
                model.AddBoolOr([])
                continue

            print(
                f"[adjacency|hard_OR]  - candidates across all types: {[c.name for c in all_candidates]}"
            )

            # At least one of these adjacencies must be true
            adj_switches: List[Any] = []
            for candidate in all_candidates:
                is_adj = model.NewBoolVar(f"is_adj_{room.name}_{candidate.name}")  # type: ignore
                adj_switches.append(is_adj)
                print(
                    f"[adjacency|hard_OR]    - adding conditional adjacency bool var '{is_adj.Name()}' for '{room.name}' <-> '{candidate.name}'"
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
                f"[adjacency|hard_OR]    - added OR of {[v.Name() for v in adj_switches]} (must touch at least one)"
            )


def soft_adjacency_constraints(
    model: cp_model.CpModel,
    rooms_list: List[Room],
    softRelations: List[RoomRelationsConstraintBase],
    min_overlap: int = 1,
) -> List[cp_model.IntVar]:
    """Apply soft (optional) adjacency relations: room SHOULD touch listed types (preference).
    
    Returns adjacency boolean variables that can be used in objective/scoring.
    Soft constraints do not enforce feasibility; they are preferences for optimization.
    """

    preference_vars: List[cp_model.IntVar] = []

    for room in rooms_list:
        matching_rules = [rel for rel in softRelations if rel.room_type == room.type]
        if not matching_rules:
            continue

        for rule in matching_rules:
            related_types = rule.related_room or []
            if not related_types:
                continue

            print(f"[adjacency|soft] Room '{room.name}' (type={room.type}) prefers adjacency with types {related_types}")

            # Collect all candidates across all types
            all_candidates: List[Room] = []
            for required_type in related_types:
                candidates = [
                    r
                    for r in rooms_list
                    if r.type == required_type and r.name != room.name
                ]
                all_candidates.extend(candidates)

            if not all_candidates:
                print(
                    f"[adjacency|soft]  - no candidates across types {related_types} for room '{room.name}'"
                )
                continue

            print(
                f"[adjacency|soft]  - candidates across all types: {[c.name for c in all_candidates]}"
            )

            # Create soft adjacency variables for each candidate
            for candidate in all_candidates:
                is_adj = model.NewBoolVar(f"soft_is_adj_{room.name}_{candidate.name}")  # type: ignore
                preference_vars.append(is_adj)
                print(
                    f"[adjacency|soft]    - adding soft adjacency bool var '{is_adj.Name()}' for '{room.name}' <-> '{candidate.name}'"
                )
                _conditional_constraint(
                    model,
                    room,
                    candidate,
                    enforcer=is_adj,
                    min_overlap=min_overlap,
                )

    return preference_vars


def adjacency_constraints(
    model: cp_model.CpModel,
    rooms_list: List[Room],
    hard_AND_Relations: Optional[List[RoomRelationsConstraintBase]] = None,
    hard_OR_Relations: Optional[List[RoomRelationsConstraintBase]] = None,
    softRelations: Optional[List[RoomRelationsConstraintBase]] = None,
    min_overlap: int = 1,
) -> List[cp_model.IntVar]:
    """Apply all types of adjacency constraints.

    Args:
        hard_AND_Relations: Room MUST touch ALL listed types (AND logic).
        hard_OR_Relations: Room MUST touch AT LEAST ONE of listed types (OR logic).
        softRelations: Room preferably touches listed types (optional, for optimization).
        min_overlap: Minimum overlap in units for two rooms to be considered adjacent.

    Returns: List of soft adjacency preference variables. Empty list if no soft relations.
    """

    soft_preference_vars: List[cp_model.IntVar] = []

    # Apply hard AND constraints
    if isinstance(hard_AND_Relations, list) and hard_AND_Relations:
        hard_AND_adjacency_constraints(model, rooms_list, hard_AND_Relations, min_overlap=min_overlap)

    # Apply hard OR constraints
    if isinstance(hard_OR_Relations, list) and hard_OR_Relations:
        hard_OR_adjacency_constraints(model, rooms_list, hard_OR_Relations, min_overlap=min_overlap)

    # Apply soft constraints and collect preference variables
    if isinstance(softRelations, list) and softRelations:
        soft_preference_vars = soft_adjacency_constraints(model, rooms_list, softRelations, min_overlap=min_overlap)

    return soft_preference_vars

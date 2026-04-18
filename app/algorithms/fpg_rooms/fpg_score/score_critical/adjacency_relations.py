from __future__ import annotations

from typing import Any, Dict, List, Sequence

from app.core.fpg_rooms.config_score import SCORE_VALIDATION_MIN_OVERLAP

from ..utils import touches_with_min_overlap


def validate_adjacency_relations(
    solution: Sequence[Dict[str, Any]],
    relation_constraints: Sequence[Any],
    min_overlap: int = SCORE_VALIDATION_MIN_OVERLAP,
) -> List[str]:
    """Validate hard adjacency relations against solved rectangles.

    Semantics mirror constraint code: for each rule attached to room_type,
    each required type in related_room must be satisfied independently
    (AND across required types, OR across matching candidates per type).
    """
    violations: List[str] = []

    rooms_by_type: Dict[str, List[Dict[str, Any]]] = {}
    for room in solution:
        rooms_by_type.setdefault(str(room["type"]), []).append(room)

    for room in solution:
        room_type = str(room["type"])
        room_name = str(room["name"])

        matching_rules = [
            r
            for r in relation_constraints
            if getattr(r, "room_type", None) == room_type
            or (isinstance(r, dict) and r.get("room_type") == room_type)
        ]
        if not matching_rules:
            continue

        for rule in matching_rules:
            related = getattr(rule, "related_room", None)
            if related is None and isinstance(rule, dict):
                related = rule.get("related_room")

            related_types = related or []
            for required_type in related_types:
                candidates = [
                    r
                    for r in rooms_by_type.get(str(required_type), [])
                    if str(r["name"]) != room_name
                ]

                if not candidates:
                    violations.append(
                        f"Adjacency rule unsatisfied for '{room_name}' ({room_type}): "
                        f"no candidate room of type '{required_type}'"
                    )
                    continue

                has_touch = any(
                    touches_with_min_overlap(room, candidate, min_overlap)
                    for candidate in candidates
                )
                if not has_touch:
                    violations.append(
                        f"Adjacency rule unsatisfied for '{room_name}' ({room_type}): "
                        f"must touch at least one room of type '{required_type}'"
                    )

    print(f"\nAdjacency Violation: {violations}\n")
    return violations

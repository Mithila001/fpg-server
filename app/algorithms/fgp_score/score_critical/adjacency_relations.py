from __future__ import annotations

from typing import Any, Dict, List, Sequence

from shapely.geometry import LineString, Polygon

from app.algorithms.types.domain import ProcessedRoomData
from app.core.fpg_rooms.config_score import SCORE_VALIDATION_MIN_OVERLAP


def _get_constraint_level(rule: Any) -> str:
    if isinstance(rule, dict):
        constraint_level = rule.get("constraint_level")
    else:
        constraint_level = getattr(rule, "constraint_level", None)
    return str(constraint_level or "").strip().lower()


def _get_related_room_types(rule: Any) -> list[str]:
    if isinstance(rule, dict):
        related = rule.get("related_room")
    else:
        related = getattr(rule, "related_room", None)
    if related is None:
        return []
    if isinstance(related, list):
        return [str(x) for x in related if x is not None]
    # Be defensive: accept tuples/sets as well.
    if isinstance(related, (tuple, set)):
        return [str(x) for x in related if x is not None]
    return []


def _sum_linestring_length(geom: Any) -> float:
    """Sum length for any line-like geometry returned by shapely intersections."""
    if geom is None or getattr(geom, "is_empty", True):
        return 0.0

    geom_type = getattr(geom, "geom_type", None)
    if geom_type == "LineString":
        return float(geom.length)
    if geom_type == "MultiLineString":
        return float(sum(float(g.length) for g in geom.geoms))
    if geom_type == "GeometryCollection":
        return float(sum(_sum_linestring_length(g) for g in geom.geoms))

    # MultiPoint / Point / Polygon => not a shared boundary segment.
    return 0.0


def touches_with_min_overlap(
    poly_a: Polygon,
    poly_b: Polygon,
    *,
    min_overlap: float,
    tolerance: float,
) -> bool:
    """Return True if two rectilinear polygons share boundary length >= min_overlap."""
    shared = poly_a.boundary.intersection(poly_b.boundary)
    shared_length = _sum_linestring_length(shared)
    return shared_length >= float(min_overlap) - float(tolerance)


def validate_adjacency_relations(
    post_processed_floor_plan: Sequence[ProcessedRoomData],
    relation_constraints: Sequence[Any],
    *,
    min_overlap: int = SCORE_VALIDATION_MIN_OVERLAP,
    tolerance: float = 1e-6,
) -> List[str]:
    """Validate hard adjacency relations against solved rectilinear polygons.

    Semantics mirror legacy `fpg_rooms` adjacency relation scoring:
    - hard_and: for every type in related_room, the room must touch >=1 room of that type
    - hard_or: the room must touch >=1 room across all types in related_room
    """
    violations: List[str] = []

    # Precompute shapely polygons once for speed and consistency.
    polygons: List[Polygon] = []
    for room in post_processed_floor_plan:
        polygons.append(Polygon(room.vertices))

    rooms_by_type: Dict[str, list[int]] = {}
    for idx, room in enumerate(post_processed_floor_plan):
        room_type = str(getattr(room, "type", "") or "")
        rooms_by_type.setdefault(room_type, []).append(idx)

    for room_idx, room in enumerate(post_processed_floor_plan):
        room_type = str(getattr(room, "type", "") or "")
        room_name = str(getattr(room, "name", "") or "")

        # Find rules attached to this room type.
        matching_rules = [
            r
            for r in relation_constraints
            if getattr(r, "room_type", None) == room_type
            or (isinstance(r, dict) and r.get("room_type") == room_type)
        ]
        if not matching_rules:
            continue

        poly_room = polygons[room_idx]
        for rule in matching_rules:
            related_types = _get_related_room_types(rule)
            if not related_types:
                continue

            constraint_level = _get_constraint_level(rule)

            if constraint_level == "hard_and":
                for required_type in related_types:
                    candidate_indices = [
                        idx
                        for idx in rooms_by_type.get(str(required_type), [])
                        if str(post_processed_floor_plan[idx].name) != room_name
                    ]
                    if not candidate_indices:
                        violations.append(
                            f"Adjacency rule unsatisfied for '{room_name}' ({room_type}): "
                            f"no candidate room of type '{required_type}'"
                        )
                        continue

                    has_touch = any(
                        touches_with_min_overlap(
                            poly_room,
                            polygons[candidate_idx],
                            min_overlap=min_overlap,
                            tolerance=tolerance,
                        )
                        for candidate_idx in candidate_indices
                    )
                    if not has_touch:
                        violations.append(
                            f"Adjacency rule unsatisfied for '{room_name}' ({room_type}): "
                            f"must touch at least one room of type '{required_type}'"
                        )

            elif constraint_level == "hard_or":
                candidate_indices: list[int] = []
                for required_type in related_types:
                    candidate_indices.extend(
                        [
                            idx
                            for idx in rooms_by_type.get(str(required_type), [])
                            if str(post_processed_floor_plan[idx].name) != room_name
                        ]
                    )

                if not candidate_indices:
                    violations.append(
                        f"Adjacency rule unsatisfied for '{room_name}' ({room_type}): "
                        f"no candidate room of any required type ({' or '.join(map(str, related_types))})"
                    )
                    continue

                has_touch = any(
                    touches_with_min_overlap(
                        poly_room,
                        polygons[candidate_idx],
                        min_overlap=min_overlap,
                        tolerance=tolerance,
                    )
                    for candidate_idx in candidate_indices
                )
                if not has_touch:
                    violations.append(
                        f"Adjacency rule unsatisfied for '{room_name}' ({room_type}): "
                        f"must touch at least one room of type ({' or '.join(map(str, related_types))})"
                    )
            else:
                raise ValueError(
                    f"Unknown constraint_level '{constraint_level}' for adjacency rule on room_type '{room_type}'"
                )

    return violations


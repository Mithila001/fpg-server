from __future__ import annotations

import math

from ..zone_utils import compute_zone, is_in_zone_range
from ...types import GraphNode


def _nodes_of_type(nodes: list[GraphNode], room_types: set[str]) -> list[GraphNode]:
    return [node for node in nodes if node.room_type in room_types]


def _ratio_score(flags: list[bool], max_score: float) -> float:
    if not flags:
        return max_score
    return (sum(1 for flag in flags if flag) / len(flags)) * max_score


def _clamp_score(score: float, max_score: float) -> float:
    return max(0.0, min(max_score, score))


def _layout_diagonal(width: float, height: float) -> float:
    return max(1.0, math.hypot(width, height))


def _relation_room_types(raw_relation: object) -> tuple[str, list[str]]:
    if isinstance(raw_relation, dict):
        room_type = str(raw_relation.get("room_type", "")).strip()
        related_room = raw_relation.get("related_room") or []
    else:
        room_type = str(getattr(raw_relation, "room_type", "")).strip()
        related_room = getattr(raw_relation, "related_room", []) or []

    related_types = [str(item).strip() for item in related_room if str(item).strip()]
    return room_type, related_types


def _nodes_by_type(nodes: list[GraphNode]) -> dict[str, list[GraphNode]]:
    node_map: dict[str, list[GraphNode]] = {}
    for node in nodes:
        node_map.setdefault(node.room_type, []).append(node)
    return node_map


def _explicit_bedroom_attached_bathroom_pairs(
    nodes: list[GraphNode],
    relation_constraints: list[object],
) -> list[tuple[GraphNode, GraphNode]]:
    node_map = _nodes_by_type(nodes)
    bedrooms = node_map.get("bedroom", [])
    attached_bathrooms = node_map.get("attachedBathroom", [])

    if not bedrooms or not attached_bathrooms:
        return []

    explicit_pairs: list[tuple[GraphNode, GraphNode]] = []
    seen_pair_ids: set[tuple[str, str]] = set()

    for raw_relation in relation_constraints:
        room_type, related_types = _relation_room_types(raw_relation)
        if not room_type or not related_types:
            continue

        room_type_norm = room_type.lower()
        related_types_norm = {related_type.lower() for related_type in related_types}

        if room_type_norm == "bedroom" and "attachedbathroom" in related_types_norm:
            subjects = bedrooms
            targets = attached_bathrooms
        elif room_type_norm == "attachedbathroom" and "bedroom" in related_types_norm:
            subjects = attached_bathrooms
            targets = bedrooms
        else:
            continue

        for subject in subjects:
            for target in targets:
                low_id, high_id = sorted((subject.id, target.id))
                pair_key = (low_id, high_id)
                if pair_key in seen_pair_ids:
                    continue
                seen_pair_ids.add(pair_key)
                if subject.room_type == "bedroom":
                    explicit_pairs.append((subject, target))
                else:
                    explicit_pairs.append((target, subject))

    return explicit_pairs


def _pair_proximity_score(node_a: GraphNode, node_b: GraphNode, max_score: float, diagonal: float) -> float:
    distance = math.hypot(node_b.x - node_a.x, node_b.y - node_a.y)
    closeness = max(0.0, 1.0 - (distance / diagonal))
    return _clamp_score(closeness * max_score, max_score)


def evaluate_room_location_soft(
    nodes: list[GraphNode],
    min_x: float,
    min_y: float,
    width: float,
    height: float,
    relation_constraints: list[object] | None = None,
) -> dict[str, float]:
    relation_constraints = relation_constraints or []
    
    # print(f"\nGraph Nodes : {nodes}\n" )

    living_nodes = _nodes_of_type(nodes, {"livingRoom"})
    living_ok = [
        is_in_zone_range(
            compute_zone(node.x, node.y, min_x, min_y, width, height),
            (1, 1),
            (3, 2),
        )
        for node in living_nodes
    ]

    bathroom_nodes = _nodes_of_type(nodes, {"bathroom", "attachedBathroom"})
    bathrooms_ok = []
    for node in bathroom_nodes:
        zone = compute_zone(node.x, node.y, min_x, min_y, width, height)
        in_bottom_row = is_in_zone_range(zone, (1, 1), (3, 1))
        in_center = zone == (2, 2)
        bathrooms_ok.append((not in_bottom_row) and (not in_center))

    dining_nodes = _nodes_of_type(nodes, {"diningRoom"})
    dining_ok = []
    for node in dining_nodes:
        zone = compute_zone(node.x, node.y, min_x, min_y, width, height)
        in_bad_zone = zone == (2, 1) or is_in_zone_range(zone, (1, 3), (3, 3))
        dining_ok.append(not in_bad_zone)

    explicit_pairs = _explicit_bedroom_attached_bathroom_pairs(nodes, relation_constraints)
    diagonal = _layout_diagonal(width, height)
    if explicit_pairs:
        pair_scores = [
            _pair_proximity_score(bedroom, attached_bathroom, 10.0, diagonal)
            for bedroom, attached_bathroom in explicit_pairs
        ]
        bedroom_attached_bathroom_proximity_score = sum(pair_scores) / len(pair_scores)
    else:
        bedroom_attached_bathroom_proximity_score = 10.0

    return {
        "living_room_zone_score": _ratio_score(living_ok, 15.0),
        "bathroom_zone_score": _ratio_score(bathrooms_ok, 15.0),
        "dining_room_zone_score": _ratio_score(dining_ok, 10.0),
        "bedroom_attached_bathroom_proximity_score": bedroom_attached_bathroom_proximity_score,
    }

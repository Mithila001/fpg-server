from __future__ import annotations

import math

from ..zone_utils import compute_zone, is_in_zone_range
from app.algorithms.types.graph import GraphNode

from app.core.fpg_rooms.config_fpg import PRIVATE_ROOM_TYPES, PUBLIC_ROOM_TYPES


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


def _pair_proximity_score(
    node_a: GraphNode, node_b: GraphNode, max_score: float, diagonal: float
) -> float:
    distance = math.hypot(node_b.x - node_a.x, node_b.y - node_a.y)
    closeness = max(0.0, 1.0 - (distance / diagonal))
    return _clamp_score(closeness * max_score, max_score)


SCORE_WEIGHT_PARAMETERS = {
    "living_room": 12.0,
    "bathroom": 12.0,
    "dining_room": 8.0,
    "hallway_purity": 5.0,
    "bedroom_bath_proximity": 8.0,
    "hallway_count_logic": 5.0,
}


def evaluate_room_location_soft(
    nodes: list[GraphNode],
    min_x: float,
    min_y: float,
    width: float,
    height: float,
    relation_constraints: list[object] | None = None,
) -> dict[str, float]:
    """
    Evaluates the room layout.
    Total score is out of 50.
    If only 1 hallway exists, the 'hallway_count_score' is 0 (effectively reducing total by 5).
    """
    relation_constraints = relation_constraints or []
    diagonal = _layout_diagonal(width, height)
    w = SCORE_WEIGHT_PARAMETERS

    # 1. Living Room Scoring
    living_nodes = _nodes_of_type(nodes, {"livingRoom"})
    living_ok = [
        is_in_zone_range(
            compute_zone(n.x, n.y, min_x, min_y, width, height), (1, 1), (3, 2)
        )
        for n in living_nodes
    ]

    # 2. Bathroom Scoring
    bathroom_nodes = _nodes_of_type(nodes, {"bathroom", "attachedBathroom"})
    bathrooms_ok = []
    for node in bathroom_nodes:
        zone = compute_zone(node.x, node.y, min_x, min_y, width, height)
        bathrooms_ok.append(
            not is_in_zone_range(zone, (1, 1), (3, 1)) and zone != (2, 2)
        )

    # 3. Dining Room Scoring
    dining_nodes = _nodes_of_type(nodes, {"diningRoom"})
    dining_ok = [
        not (
            compute_zone(n.x, n.y, min_x, min_y, width, height) == (2, 1)
            or is_in_zone_range(
                compute_zone(n.x, n.y, min_x, min_y, width, height), (1, 3), (3, 3)
            )
        )
        for n in dining_nodes
    ]

    # 4. Hallway Purity
    hallway_nodes = _nodes_of_type(nodes, {"hallway"})
    other_rooms = [n for n in nodes if n.room_type != "hallway"]
    hallway_purity_score = _calculate_hallway_purity(
        hallway_nodes, other_rooms, diagonal, w["hallway_purity"]
    )

    # 5. Bed/Bath Proximity
    explicit_pairs = _explicit_bedroom_attached_bathroom_pairs(
        nodes, relation_constraints
    )
    if explicit_pairs:
        pair_scores = [
            _pair_proximity_score(
                bedroom, attached_bathroom, w["bedroom_bath_proximity"], diagonal
            )
            for bedroom, attached_bathroom in explicit_pairs
        ]
        proximity_score = sum(pair_scores) / len(pair_scores)
    else:
        proximity_score = w["bedroom_bath_proximity"]

    # 6. Hallway Count Logic
    # If exactly 1 hallway: score is 0 (Reduction). Else (0 or >1): score is full weight (Addition).
    hallway_count_score = 0.0 if len(hallway_nodes) == 1 else w["hallway_count_logic"]

    return {
        "living_room_zone_score": _ratio_score(living_ok, w["living_room"]),
        "bathroom_zone_score": _ratio_score(bathrooms_ok, w["bathroom"]),
        "dining_room_zone_score": _ratio_score(dining_ok, w["dining_room"]),
        "bedroom_attached_bathroom_proximity_score": proximity_score,
        "hallway_zoning_purity_score": hallway_purity_score,
        "hallway_count_score": hallway_count_score,
    }


def _get_room_category(room_type: str) -> str | None:
    """Categorizes a room as public, private, or neutral."""

    if room_type in PUBLIC_ROOM_TYPES:
        return "public"
    if room_type in PRIVATE_ROOM_TYPES:
        return "private"
    return None  # Neutral (livingRoom, hallway, veranda, etc.)


def _calculate_hallway_purity(
    hallways: list[GraphNode], rooms: list[GraphNode], diagonal: float, max_score: float
) -> float:
    if not hallways:
        return max_score

    threshold = diagonal * 0.20
    hallway_scores = []

    for hallway in hallways:
        found_categories = set()
        for room in rooms:
            category = _get_room_category(room.room_type)
            if category is None:
                continue

            dist = math.hypot(room.x - hallway.x, room.y - hallway.y)
            if dist <= threshold:
                found_categories.add(category)

        # Binary purity check: 1.0 if pure or empty, 0.0 if polluted
        hallway_scores.append(0.0 if len(found_categories) > 1 else 1.0)

    return (sum(hallway_scores) / len(hallway_scores)) * max_score

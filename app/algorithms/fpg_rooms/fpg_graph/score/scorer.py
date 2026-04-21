from __future__ import annotations

import math
from typing import Any

from ..adapters import node_lookup
from ..types import GraphEdge, GraphNode, GraphScoreBreakdown


def _coerce_relation(rule: Any) -> tuple[str, list[str], str] | None:
    if isinstance(rule, dict):
        room_type = str(rule.get("room_type", "")).strip()
        related = rule.get("related_room") or []
        level = str(rule.get("constraint_level", "")).strip()
    else:
        room_type = str(getattr(rule, "room_type", "")).strip()
        related = getattr(rule, "related_room", []) or []
        level = str(getattr(rule, "constraint_level", "")).strip()

    if not room_type:
        return None

    related_types = [str(item).strip() for item in related if str(item).strip()]
    return room_type, related_types, level


def _target_distance(source: GraphNode, target: GraphNode, weight: float) -> float:
    return (source.radius + target.radius) * (2.3 - 0.55 * max(0.0, min(2.0, weight)))


def _distance_score(source: GraphNode, target: GraphNode, weight: float) -> float:
    dx = target.x - source.x
    dy = target.y - source.y
    dist = math.hypot(dx, dy)
    target_dist = max(1e-6, _target_distance(source, target, weight))

    stretch = max(0.0, (dist - target_dist) / target_dist)
    return max(0.0, 1.0 - stretch)


def _distance_point_to_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    abx = bx - ax
    aby = by - ay
    denom = abx * abx + aby * aby
    if denom < 1e-9:
        return math.hypot(px - ax, py - ay)

    apx = px - ax
    apy = py - ay
    t = (apx * abx + apy * aby) / denom
    t = max(0.0, min(1.0, t))

    cx = ax + t * abx
    cy = ay + t * aby
    return math.hypot(px - cx, py - cy)


def _count_blockers(nodes: list[GraphNode], source: GraphNode, target: GraphNode) -> int:
    blocker_count = 0
    corridor_half_width = max(1.0, min(source.radius, target.radius) * 0.35)
    for node in nodes:
        if node.id in {source.id, target.id}:
            continue
        dist = _distance_point_to_segment(node.x, node.y, source.x, source.y, target.x, target.y)
        if dist <= node.radius + corridor_half_width:
            blocker_count += 1
    return blocker_count


def _front_bonus(nodes: list[GraphNode]) -> float:
    target_nodes = [node for node in nodes if node.room_type in {"veranda", "garage"}]
    if not target_nodes:
        return 0.0

    other_nodes = [node for node in nodes if node.room_type not in {"veranda", "garage"}]
    if not other_nodes:
        return 50.0

    min_other_y = min(node.y for node in other_nodes)
    all_front = all(node.y <= min_other_y + 1e-6 for node in target_nodes)
    return 50.0 if all_front else 0.0


def score_graph_layout(
    nodes: list[GraphNode],
    edges: list[GraphEdge],
    relation_constraints: list[Any],
) -> GraphScoreBreakdown:
    by_type: dict[str, list[GraphNode]] = {}
    for node in nodes:
        by_type.setdefault(node.room_type, []).append(node)

    _ = node_lookup(nodes)

    edge_weight_map: dict[tuple[str, str], float] = {}
    for edge in edges:
        key = tuple(sorted((edge.source_id, edge.target_id)))
        edge_weight_map[key] = max(edge_weight_map.get(key, 0.0), edge.weight)

    adjacency_quality_sum = 0.0
    adjacency_expectations = 0
    blocked_penalty = 0.0

    for raw_rule in relation_constraints:
        relation = _coerce_relation(raw_rule)
        if relation is None:
            continue

        source_type, related_types, level = relation
        source_nodes = by_type.get(source_type, [])
        if not source_nodes or not related_types:
            continue

        for source_node in source_nodes:
            if level == "hard_AND":
                related_scores: list[float] = []
                for related_type in related_types:
                    candidates = by_type.get(related_type, [])
                    best_score = 0.0
                    best_target: GraphNode | None = None
                    best_weight = 1.2
                    for candidate in candidates:
                        weight = edge_weight_map.get(tuple(sorted((source_node.id, candidate.id))), 1.2)
                        score = _distance_score(source_node, candidate, weight)
                        if score > best_score:
                            best_score = score
                            best_target = candidate
                            best_weight = weight
                    related_scores.append(best_score)
                    adjacency_expectations += 1
                    adjacency_quality_sum += best_score

                    if best_target is not None and best_score > 0.0:
                        blockers = _count_blockers(nodes, source_node, best_target)
                        blocked_penalty += min(10.0, blockers * 2.5 * best_weight)

            else:
                best_score = 0.0
                best_target = None
                best_weight = 0.9
                for related_type in related_types:
                    for candidate in by_type.get(related_type, []):
                        weight = edge_weight_map.get(tuple(sorted((source_node.id, candidate.id))), 0.9)
                        score = _distance_score(source_node, candidate, weight)
                        if score > best_score:
                            best_score = score
                            best_target = candidate
                            best_weight = weight
                adjacency_expectations += 1
                adjacency_quality_sum += best_score

                if best_target is not None and best_score > 0.0:
                    blockers = _count_blockers(nodes, source_node, best_target)
                    blocked_penalty += min(10.0, blockers * 2.5 * best_weight)

    if adjacency_expectations <= 0:
        adjacency_score = 0.0
    else:
        adjacency_score = (adjacency_quality_sum / adjacency_expectations) * 60.0

    blocked_penalty = min(40.0, blocked_penalty)
    front_bonus = _front_bonus(nodes)
    total_score = adjacency_score - blocked_penalty + front_bonus
    usable_layout = total_score > 40.0

    return GraphScoreBreakdown(
        adjacency_score=adjacency_score,
        blocked_penalty=blocked_penalty,
        front_bonus=front_bonus,
        total_score=total_score,
        usable_layout=usable_layout,
    )

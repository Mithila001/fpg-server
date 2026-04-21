from __future__ import annotations

import math
from random import Random
from typing import Any

from app.algorithms.fpg_rooms.types.room import FpgRequirements, RoomData
from app.core.fpg_rooms.config_fpg import (
    DEFAULT_HALLWAY_COUNT,
    HALLWAY_GENERATOR_MIN_HEIGHT,
    HALLWAY_GENERATOR_MIN_WIDTH,
    HALLWAY_LONG_SIDE_MIN,
)

from .types import GraphBoundary, GraphEdge, GraphNode


def _midpoint(value_a: float, value_b: float) -> float:
    return (float(value_a) + float(value_b)) / 2.0


def _room_radius(room: RoomData) -> float:
    mid_w = _midpoint(room.min_w, room.max_w)
    mid_h = _midpoint(room.min_h, room.max_h)
    return max(1.0, min(mid_w, mid_h) / 2.0)


def build_boundary(requirements: FpgRequirements) -> GraphBoundary:
    return GraphBoundary(
        width=float(requirements.config.floor_plan_width),
        height=float(requirements.config.floor_plan_height),
    )


def build_nodes(
    requirements: FpgRequirements,
    hallway_count_override: int | None = None,
) -> list[GraphNode]:
    nodes: list[GraphNode] = []

    for index, room in enumerate(requirements.rooms):
        nodes.append(
            GraphNode(
                id=f"room_{index}",
                name=room.name,
                room_type=room.type,
                radius=_room_radius(room),
            )
        )

    existing_hallways = sum(1 for node in nodes if node.room_type == "hallway")
    config_hallway_count = int(getattr(requirements.config, "hallway_count", DEFAULT_HALLWAY_COUNT))
    target_hallway_count = hallway_count_override if hallway_count_override is not None else config_hallway_count
    target_hallway_count = max(0, target_hallway_count)

    missing_hallways = max(0, target_hallway_count - existing_hallways)
    hallway_radius = max(
        1.0,
        min(
            _midpoint(HALLWAY_GENERATOR_MIN_WIDTH, HALLWAY_LONG_SIDE_MIN),
            _midpoint(HALLWAY_GENERATOR_MIN_HEIGHT, HALLWAY_LONG_SIDE_MIN),
        ) / 2.0,
    )

    for index in range(missing_hallways):
        nodes.append(
            GraphNode(
                id=f"hallway_generated_{index}",
                name=f"hallwayGenerated{index + 1}",
                room_type="hallway",
                radius=hallway_radius,
                synthesized=True,
            )
        )

    return nodes


def _coerce_relation(rule: Any) -> tuple[str, list[str], str] | None:
    if isinstance(rule, dict):
        room_type = str(rule.get("room_type", "")).strip()
        related = rule.get("related_room") or []
        constraint_level = str(rule.get("constraint_level", "")).strip()
    else:
        room_type = str(getattr(rule, "room_type", "")).strip()
        related = getattr(rule, "related_room", []) or []
        constraint_level = str(getattr(rule, "constraint_level", "")).strip()

    if not room_type:
        return None

    related_types = [str(item).strip() for item in related if str(item).strip()]
    return room_type, related_types, constraint_level


def _default_weight_for_level(level: str) -> float:
    if level == "hard_AND":
        return 1.2
    if level == "hard_OR":
        return 0.9
    return 1.0


def build_edges(
    nodes: list[GraphNode],
    relation_constraints: list[Any],
) -> list[GraphEdge]:
    nodes_by_type: dict[str, list[GraphNode]] = {}
    for node in nodes:
        nodes_by_type.setdefault(node.room_type, []).append(node)

    weighted_pairs: dict[tuple[str, str], GraphEdge] = {}

    def add_pair(source_id: str, target_id: str, weight: float, rule_kind: str) -> None:
        if source_id == target_id:
            return
        low_id, high_id = sorted((source_id, target_id))
        key = (low_id, high_id)
        edge = weighted_pairs.get(key)
        if edge is None or weight > edge.weight:
            weighted_pairs[key] = GraphEdge(
                source_id=low_id,
                target_id=high_id,
                weight=max(0.0, min(2.0, weight)),
                rule_kind=rule_kind,
            )

    for raw_rule in relation_constraints:
        relation = _coerce_relation(raw_rule)
        if relation is None:
            continue
        room_type, related_types, constraint_level = relation
        weight = _default_weight_for_level(constraint_level)
        subjects = nodes_by_type.get(room_type, [])

        for subject in subjects:
            for related_type in related_types:
                for target in nodes_by_type.get(related_type, []):
                    add_pair(subject.id, target.id, weight, constraint_level or "relation")

    dining_rooms = nodes_by_type.get("diningRoom", [])
    living_rooms = nodes_by_type.get("livingRoom", [])
    kitchens = nodes_by_type.get("kitchen", [])
    hallways = nodes_by_type.get("hallway", [])

    for dining in dining_rooms:
        for living in living_rooms:
            add_pair(dining.id, living.id, 1.35, "dining_path")
        for kitchen in kitchens:
            add_pair(dining.id, kitchen.id, 1.35, "dining_path")
        for hallway in hallways:
            add_pair(dining.id, hallway.id, 1.05, "dining_hallway")

    return list(weighted_pairs.values())


def initialize_positions(
    nodes: list[GraphNode],
    boundary: GraphBoundary,
    seed: int | None,
) -> None:
    rng = Random(seed)

    for node in nodes:
        min_x = node.radius
        max_x = max(min_x, boundary.width - node.radius)
        min_y = node.radius
        max_y = max(min_y, boundary.height - node.radius)

        node.x = rng.uniform(min_x, max_x)

        # Front-biased initialization for garage/veranda because front is y=0.
        if node.room_type in {"veranda", "garage"}:
            front_band = min(max_y, max(min_y, boundary.height * 0.2))
            node.y = rng.uniform(min_y, front_band)
        else:
            node.y = rng.uniform(min_y, max_y)

        node.vx = 0.0
        node.vy = 0.0


def node_lookup(nodes: list[GraphNode]) -> dict[str, GraphNode]:
    return {node.id: node for node in nodes}


def pair_distance(node_a: GraphNode, node_b: GraphNode) -> float:
    return math.hypot(node_b.x - node_a.x, node_b.y - node_a.y)

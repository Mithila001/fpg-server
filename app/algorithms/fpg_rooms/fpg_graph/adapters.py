from __future__ import annotations

import math
from random import Random
from typing import Any

from app.algorithms.types import FpgRequirements, RoomData
from app.core.fpg_rooms.config_fpg import (
    DEFAULT_HALLWAY_COUNT,
    HALLWAY_GENERATOR_MIN_HEIGHT,
    HALLWAY_GENERATOR_MIN_WIDTH,
    HALLWAY_LONG_SIDE_MIN,
    PUBLIC_ROOM_TYPES,
    PRIVATE_ROOM_TYPES,
)

from app.algorithms.types.solvers import GraphBoundary, GraphEdge, GraphNode

UNIQUE_RELATION_REQUIRED_ROOM_TYPES = ["attachedBathroom"]


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
    config_hallway_count = int(
        getattr(requirements.config, "hallway_count", DEFAULT_HALLWAY_COUNT)
    )
    target_hallway_count = max(0, config_hallway_count)

    missing_hallways = max(0, target_hallway_count - existing_hallways)
    hallway_radius = max(
        1.0,
        min(
            _midpoint(HALLWAY_GENERATOR_MIN_WIDTH, HALLWAY_LONG_SIDE_MIN),
            _midpoint(HALLWAY_GENERATOR_MIN_HEIGHT, HALLWAY_LONG_SIDE_MIN),
        )
        / 2.0,
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
    assignments: dict[str, list[str]] = {}

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

    def _node_degree(node_id: str) -> int:
        degree = 0
        for edge in weighted_pairs.values():
            if edge.source_id == node_id or edge.target_id == node_id:
                degree += 1
        return degree

    # 1. Process explicit Relation Constraints (Keep your existing logic here)
    for raw_rule in relation_constraints:
        relation = _coerce_relation(raw_rule)
        if relation is None:
            continue
        room_type, related_types, constraint_level = relation
        weight = _default_weight_for_level(constraint_level)
        subjects = nodes_by_type.get(room_type, [])
        for subject in subjects:
            for rel_type in related_types:
                targets = nodes_by_type.get(rel_type, [])
                if not targets:
                    continue
                best_target = None
                if room_type in UNIQUE_RELATION_REQUIRED_ROOM_TYPES:
                    available_targets = [t for t in targets if t.id not in assignments]
                    best_target = (
                        min(available_targets, key=lambda t: pair_distance(subject, t))
                        if available_targets
                        else min(targets, key=lambda t: pair_distance(subject, t))
                    )
                else:
                    best_target = min(targets, key=lambda t: pair_distance(subject, t))
                if best_target:
                    add_pair(
                        subject.id,
                        best_target.id,
                        weight,
                        constraint_level or "relation",
                    )
                    assignments.setdefault(best_target.id, []).append(subject.id)

    # 2. NEW Hallway Logic
    hallways = nodes_by_type.get("hallway", [])
    hallway_count = len(hallways)

    # Gather all potential room nodes excluding hallways and verandas
    all_rooms = [
        n for n in nodes if n.room_type != "hallway" and n.room_type != "veranda"
    ]
    public_rooms = [n for n in all_rooms if n.room_type in PUBLIC_ROOM_TYPES]
    private_rooms = [n for n in all_rooms if n.room_type in PRIVATE_ROOM_TYPES]

    def _hallways_by_index_parity() -> tuple[list[GraphNode], list[GraphNode]]:
        odd_hallways: list[GraphNode] = []
        even_hallways: list[GraphNode] = []
        for index, hallway in enumerate(hallways, start=1):
            if index % 2 == 0:
                even_hallways.append(hallway)
            else:
                odd_hallways.append(hallway)
        return odd_hallways, even_hallways

    def _connect_rooms(
        rooms: list[GraphNode],
        hallway_targets: list[GraphNode],
        rule_kind: str,
        *,
        connect_all_targets: bool,
    ) -> None:
        if not rooms or not hallway_targets:
            return

        for room in rooms:
            if connect_all_targets:
                for hallway in hallway_targets:
                    add_pair(room.id, hallway.id, 1.0, rule_kind)
            else:
                closest_hallway = min(
                    hallway_targets,
                    key=lambda hallway: pair_distance(room, hallway),
                )
                add_pair(room.id, closest_hallway.id, 1.0, rule_kind)

    if hallway_count == 1:
        # Rule: Single hallway connects to all non-veranda rooms.
        for room in all_rooms:
            closest_hallway = min(hallways, key=lambda h: pair_distance(room, h))
            add_pair(room.id, closest_hallway.id, 1.0, "hallway_universal")
    elif hallway_count >= 2:
        # Rule: odd-indexed hallways serve private rooms, even-indexed hallways serve public rooms.
        private_hallways, public_hallways = _hallways_by_index_parity()
        connect_all_targets = hallway_count == 4

        _connect_rooms(
            public_rooms,
            public_hallways,
            "hallway_public_even",
            connect_all_targets=connect_all_targets,
        )
        _connect_rooms(
            private_rooms,
            private_hallways,
            "hallway_private_odd",
            connect_all_targets=connect_all_targets,
        )

    # Ensure every hallway participates in the graph connectivity when possible.
    living_rooms = nodes_by_type.get("livingRoom", [])
    non_veranda_rooms = [n for n in nodes if n.room_type not in {"hallway", "veranda"}]
    for hallway in hallways:
        if _node_degree(hallway.id) > 0:
            continue

        fallback_room: GraphNode | None = None
        if living_rooms:
            fallback_room = min(
                living_rooms, key=lambda room: pair_distance(hallway, room)
            )
        elif non_veranda_rooms:
            fallback_room = min(
                non_veranda_rooms,
                key=lambda room: pair_distance(hallway, room),
            )

        if fallback_room is not None:
            add_pair(
                fallback_room.id,
                hallway.id,
                0.95,
                "hallway_coverage_fallback",
            )

    # 3. Existing Dining Path Logic (Optional: Keep or remove based on preference)
    dining_rooms = nodes_by_type.get("diningRoom", [])
    living_rooms = nodes_by_type.get("livingRoom", [])
    kitchens = nodes_by_type.get("kitchen", [])
    for dining in dining_rooms:
        if living_rooms:
            closest_living = min(living_rooms, key=lambda r: pair_distance(dining, r))
            add_pair(dining.id, closest_living.id, 1.3, "dining_path")
        if kitchens:
            closest_kitchen = min(kitchens, key=lambda r: pair_distance(dining, r))
            add_pair(dining.id, closest_kitchen.id, 1.3, "dining_path")

    # 4. Custom Room Connections
    living_rooms = nodes_by_type.get("livingRoom", [])
    verandas = nodes_by_type.get("veranda", [])

    for living in living_rooms:
        for veranda in verandas:
            # Setting weight to 1.3 to make it stronger than dining (1.1)
            # and hard_AND rules (1.2)
            add_pair(living.id, veranda.id, 1.3, "living_veranda_connection")

    return list(weighted_pairs.values())


def initialize_positions(
    nodes: list[GraphNode],
    boundary: GraphBoundary,
    seed: int | None,
    explicit_positions: dict[str, tuple[float, float]] | None = None,
) -> None:
    rng = Random(seed)

    for node in nodes:
        min_x = node.radius
        max_x = max(min_x, boundary.width - node.radius)
        min_y = node.radius
        max_y = max(min_y, boundary.height - node.radius)

        if explicit_positions is not None and node.id in explicit_positions:
            x, y = explicit_positions[node.id]
            node.x = min(max_x, max(min_x, float(x)))
            node.y = min(max_y, max(min_y, float(y)))
            node.vx = 0.0
            node.vy = 0.0
            continue

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

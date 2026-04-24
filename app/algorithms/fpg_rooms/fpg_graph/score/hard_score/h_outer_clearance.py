from __future__ import annotations

from app.algorithms.types.graph import GraphNode


def _nodes_of_type(nodes: list[GraphNode], room_type: str) -> list[GraphNode]:
    return [node for node in nodes if node.room_type == room_type]


def _is_direction_clear(
    node: GraphNode, all_nodes: list[GraphNode], direction: str
) -> bool:
    for other in all_nodes:
        if other.id == node.id:
            continue
        overlap_axis = node.radius + other.radius

        if direction == "front":
            if other.y < node.y and abs(other.x - node.x) <= overlap_axis:
                return False
        elif direction == "back":
            if other.y > node.y and abs(other.x - node.x) <= overlap_axis:
                return False
        elif direction == "left":
            if other.x < node.x and abs(other.y - node.y) <= overlap_axis:
                return False
        elif direction == "right":
            if other.x > node.x and abs(other.y - node.y) <= overlap_axis:
                return False

    return True


def evaluate_outer_clearance_hard(nodes: list[GraphNode]) -> dict[str, bool]:
    results: dict[str, bool] = {}

    veranda_nodes = _nodes_of_type(nodes, "veranda")
    results["veranda_front_clear"] = bool(veranda_nodes) and all(
        _is_direction_clear(node, nodes, "front") for node in veranda_nodes
    )

    garage_nodes = _nodes_of_type(nodes, "garage")
    results["garage_front_clear"] = bool(garage_nodes) and all(
        _is_direction_clear(node, nodes, "front") for node in garage_nodes
    )

    kitchen_nodes = _nodes_of_type(nodes, "kitchen")
    hallway_nodes = _nodes_of_type(nodes, "hallway")

    kitchen_any_clear = bool(kitchen_nodes) and all(
        _is_direction_clear(node, nodes, "back")
        or _is_direction_clear(node, nodes, "left")
        or _is_direction_clear(node, nodes, "right")
        for node in kitchen_nodes
    )
    hallway_back_clear = bool(hallway_nodes) and any(
        _is_direction_clear(node, nodes, "back") for node in hallway_nodes
    )
    results["kitchen_or_hallway_outer_clear"] = kitchen_any_clear or hallway_back_clear

    return results

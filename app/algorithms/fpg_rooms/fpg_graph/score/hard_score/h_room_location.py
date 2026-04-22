from __future__ import annotations

from ..zone_utils import compute_zone
from ...types import GraphNode


def _nodes_of_type(nodes: list[GraphNode], room_type: str) -> list[GraphNode]:
    return [node for node in nodes if node.room_type == room_type]


def evaluate_room_location_hard(
    nodes: list[GraphNode],
    min_x: float,
    min_y: float,
    width: float,
    height: float,
) -> dict[str, bool]:
    results: dict[str, bool] = {}

    veranda_nodes = _nodes_of_type(nodes, "veranda")
    results["veranda_in_bottom_row"] = bool(veranda_nodes) and all(
        compute_zone(node.x, node.y, min_x, min_y, width, height)[1] == 1 for node in veranda_nodes
    )

    garage_nodes = _nodes_of_type(nodes, "garage")
    results["garage_in_bottom_corner"] = bool(garage_nodes) and all(
        (zone_x, zone_y) in {(1, 1), (3, 1)}
        for zone_x, zone_y in [compute_zone(node.x, node.y, min_x, min_y, width, height) for node in garage_nodes]
    )

    kitchen_nodes = _nodes_of_type(nodes, "kitchen")
    results["kitchen_in_center"] = bool(kitchen_nodes) and all(
        compute_zone(node.x, node.y, min_x, min_y, width, height) == (2, 2) for node in kitchen_nodes
    )

    hallway_nodes = _nodes_of_type(nodes, "hallway")
    results["hallway_not_in_bottom_row"] = bool(hallway_nodes) and all(
        compute_zone(node.x, node.y, min_x, min_y, width, height)[1] != 1 for node in hallway_nodes
    )

    return results

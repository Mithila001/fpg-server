from __future__ import annotations

from ..zone_utils import compute_zone, is_in_zone_range
from ...types import GraphNode


def _nodes_of_type(nodes: list[GraphNode], room_types: set[str]) -> list[GraphNode]:
    return [node for node in nodes if node.room_type in room_types]


def _ratio_score(flags: list[bool], max_score: float) -> float:
    if not flags:
        return max_score
    return (sum(1 for flag in flags if flag) / len(flags)) * max_score


def evaluate_room_location_soft(
    nodes: list[GraphNode],
    min_x: float,
    min_y: float,
    width: float,
    height: float,
) -> dict[str, float]:
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

    return {
        "living_room_zone_score": _ratio_score(living_ok, 25.0),
        "bathroom_zone_score": _ratio_score(bathrooms_ok, 25.0),
    }

from __future__ import annotations

from app.algorithms.fpg_rooms.fpg_graph.adapters import build_edges
from app.algorithms.types.solvers import GraphNode


def _degree_by_id(edges: list, node_id: str) -> int:
    return sum(
        1 for edge in edges if edge.source_id == node_id or edge.target_id == node_id
    )


def _edge_between(edges: list, id_a: str, id_b: str):
    low_id, high_id = sorted((id_a, id_b))
    for edge in edges:
        if edge.source_id == low_id and edge.target_id == high_id:
            return edge
    return None


def test_hallway_count_two_assigns_fallback_for_uncovered_private_hallway() -> None:
    nodes = [
        GraphNode(
            id="hall_0", name="hallway1", room_type="hallway", radius=2.0, x=10, y=10
        ),
        GraphNode(
            id="hall_1", name="hallway2", room_type="hallway", radius=2.0, x=80, y=80
        ),
        GraphNode(
            id="living_0",
            name="livingRoom1",
            room_type="livingRoom",
            radius=5.0,
            x=75,
            y=78,
        ),
        GraphNode(
            id="kitchen_0", name="kitchen1", room_type="kitchen", radius=4.0, x=12, y=12
        ),
        GraphNode(
            id="dining_0",
            name="diningRoom1",
            room_type="diningRoom",
            radius=4.0,
            x=15,
            y=9,
        ),
    ]

    edges = build_edges(nodes=nodes, relation_constraints=[])

    assert _degree_by_id(edges, "hall_0") > 0
    assert _degree_by_id(edges, "hall_1") > 0
    assert any(edge.rule_kind == "hallway_coverage_fallback" for edge in edges)


def test_hallway_count_three_no_hallway_isolated_with_sparse_private_rooms() -> None:
    nodes = [
        GraphNode(
            id="hall_0", name="hallway1", room_type="hallway", radius=2.0, x=10, y=10
        ),
        GraphNode(
            id="hall_1", name="hallway2", room_type="hallway", radius=2.0, x=40, y=40
        ),
        GraphNode(
            id="hall_2", name="hallway3", room_type="hallway", radius=2.0, x=80, y=80
        ),
        GraphNode(
            id="living_0",
            name="livingRoom1",
            room_type="livingRoom",
            radius=5.0,
            x=12,
            y=8,
        ),
        GraphNode(
            id="bed_0", name="bedroom1", room_type="bedroom", radius=4.0, x=9, y=11
        ),
        GraphNode(
            id="kitchen_0", name="kitchen1", room_type="kitchen", radius=4.0, x=20, y=12
        ),
    ]

    edges = build_edges(nodes=nodes, relation_constraints=[])

    hallway_ids = ["hall_0", "hall_1", "hall_2"]
    assert all(_degree_by_id(edges, hallway_id) > 0 for hallway_id in hallway_ids)


def test_hallway_count_four_no_hallway_isolated_with_sparse_public_rooms() -> None:
    nodes = [
        GraphNode(
            id="hall_0", name="hallway1", room_type="hallway", radius=2.0, x=10, y=10
        ),
        GraphNode(
            id="hall_1", name="hallway2", room_type="hallway", radius=2.0, x=30, y=30
        ),
        GraphNode(
            id="hall_2", name="hallway3", room_type="hallway", radius=2.0, x=50, y=50
        ),
        GraphNode(
            id="hall_3", name="hallway4", room_type="hallway", radius=2.0, x=70, y=70
        ),
        GraphNode(
            id="living_0",
            name="livingRoom1",
            room_type="livingRoom",
            radius=5.0,
            x=65,
            y=66,
        ),
        GraphNode(
            id="kitchen_0", name="kitchen1", room_type="kitchen", radius=4.0, x=68, y=71
        ),
        GraphNode(
            id="dining_0",
            name="diningRoom1",
            room_type="diningRoom",
            radius=4.0,
            x=69,
            y=74,
        ),
    ]

    edges = build_edges(nodes=nodes, relation_constraints=[])

    hallway_ids = ["hall_0", "hall_1", "hall_2", "hall_3"]
    assert all(_degree_by_id(edges, hallway_id) > 0 for hallway_id in hallway_ids)


def test_hallway_count_one_keeps_original_behavior_without_fallback_requirement() -> (
    None
):
    nodes = [
        GraphNode(
            id="hall_0", name="hallway1", room_type="hallway", radius=2.0, x=10, y=10
        ),
        GraphNode(
            id="living_0",
            name="livingRoom1",
            room_type="livingRoom",
            radius=5.0,
            x=14,
            y=14,
        ),
        GraphNode(
            id="bed_0", name="bedroom1", room_type="bedroom", radius=4.0, x=18, y=18
        ),
    ]

    edges = build_edges(nodes=nodes, relation_constraints=[])

    assert _degree_by_id(edges, "hall_0") > 0
    assert not any(edge.rule_kind == "hallway_coverage_fallback" for edge in edges)


def test_hallway_count_three_assigns_odd_to_private_and_even_to_public() -> None:
    nodes = [
        GraphNode(
            id="hall_0", name="hallway1", room_type="hallway", radius=2.0, x=0, y=0
        ),
        GraphNode(
            id="hall_1", name="hallway2", room_type="hallway", radius=2.0, x=50, y=0
        ),
        GraphNode(
            id="hall_2", name="hallway3", room_type="hallway", radius=2.0, x=100, y=0
        ),
        GraphNode(
            id="bed_0", name="bedroom1", room_type="bedroom", radius=4.0, x=10, y=5
        ),
        GraphNode(
            id="kit_0", name="kitchen1", room_type="kitchen", radius=4.0, x=55, y=5
        ),
    ]

    edges = build_edges(nodes=nodes, relation_constraints=[])

    private_edge = _edge_between(edges, "bed_0", "hall_0")
    public_edge = _edge_between(edges, "kit_0", "hall_1")

    assert private_edge is not None
    assert private_edge.rule_kind == "hallway_private_odd"
    assert public_edge is not None
    assert public_edge.rule_kind == "hallway_public_even"


def test_hallway_count_four_connects_public_and_private_to_two_hallways_each() -> None:
    nodes = [
        GraphNode(
            id="hall_0", name="hallway1", room_type="hallway", radius=2.0, x=0, y=0
        ),
        GraphNode(
            id="hall_1", name="hallway2", room_type="hallway", radius=2.0, x=25, y=0
        ),
        GraphNode(
            id="hall_2", name="hallway3", room_type="hallway", radius=2.0, x=50, y=0
        ),
        GraphNode(
            id="hall_3", name="hallway4", room_type="hallway", radius=2.0, x=75, y=0
        ),
        GraphNode(
            id="kit_0", name="kitchen1", room_type="kitchen", radius=4.0, x=26, y=5
        ),
        GraphNode(
            id="bed_0", name="bedroom1", room_type="bedroom", radius=4.0, x=5, y=5
        ),
    ]

    edges = build_edges(nodes=nodes, relation_constraints=[])

    assert _edge_between(edges, "kit_0", "hall_1") is not None
    assert _edge_between(edges, "kit_0", "hall_3") is not None
    assert _edge_between(edges, "bed_0", "hall_0") is not None
    assert _edge_between(edges, "bed_0", "hall_2") is not None


def test_dining_path_weight_is_1_3() -> None:
    nodes = [
        GraphNode(
            id="dining_0",
            name="diningRoom1",
            room_type="diningRoom",
            radius=4.0,
            x=10,
            y=10,
        ),
        GraphNode(
            id="living_0",
            name="livingRoom1",
            room_type="livingRoom",
            radius=5.0,
            x=11,
            y=10,
        ),
    ]

    edges = build_edges(nodes=nodes, relation_constraints=[])
    dining_edge = _edge_between(edges, "dining_0", "living_0")

    assert dining_edge is not None
    assert dining_edge.rule_kind == "dining_path"
    assert dining_edge.weight == 1.3

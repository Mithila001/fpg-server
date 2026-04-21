from __future__ import annotations

from app.algorithms.fpg_rooms.fpg_graph import GraphEdge, GraphNode, run_graph_layout
from app.algorithms.fpg_rooms.fpg_graph.score import score_graph_layout
from app.algorithms.fpg_rooms.types.room import ConfigData, FpgRequirements, RoomData


def _requirements() -> FpgRequirements:
    rooms = [
        RoomData(name="livingRoom1", type="livingRoom", min_w=30, min_h=25, max_w=40, max_h=35),
        RoomData(name="bedroom1", type="bedroom", min_w=16, min_h=14, max_w=22, max_h=20),
        RoomData(name="kitchen1", type="kitchen", min_w=14, min_h=12, max_w=20, max_h=18),
        RoomData(name="veranda1", type="veranda", min_w=18, min_h=10, max_w=26, max_h=14),
        RoomData(name="garage1", type="garage", min_w=24, min_h=20, max_w=34, max_h=26),
    ]
    config = ConfigData(
        min_coverage=0.4,
        max_aspect_ratio=16.0,
        min_aspect_ratio=0.2,
        floor_plan_width=160,
        floor_plan_height=120,
        hallway_count=1,
    )
    relation_constraints = [
        {"room_type": "bedroom", "related_room": ["livingRoom", "hallway"], "constraint_level": "hard_OR"},
        {"room_type": "kitchen", "related_room": ["livingRoom", "hallway"], "constraint_level": "hard_OR"},
        {"room_type": "veranda", "related_room": ["livingRoom"], "constraint_level": "hard_AND"},
        {"room_type": "garage", "related_room": ["livingRoom", "hallway"], "constraint_level": "hard_OR"},
    ]
    return FpgRequirements(rooms=rooms, config=config, relation_constraints=relation_constraints)


def test_run_graph_layout_creates_hallway_from_config() -> None:
    requirements = _requirements()
    result = run_graph_layout(requirements=requirements, seed=7)

    hallway_nodes = [node for node in result.nodes if node.room_type == "hallway"]
    assert len(hallway_nodes) == 1


def test_run_graph_layout_is_deterministic_with_fixed_seed() -> None:
    requirements = _requirements()

    first = run_graph_layout(requirements=requirements, seed=11)
    second = run_graph_layout(requirements=requirements, seed=11)

    first_positions = sorted((node.id, round(node.x, 6), round(node.y, 6)) for node in first.nodes)
    second_positions = sorted((node.id, round(node.x, 6), round(node.y, 6)) for node in second.nodes)
    assert first_positions == second_positions


def test_run_graph_layout_keeps_nodes_inside_boundary() -> None:
    requirements = _requirements()
    result = run_graph_layout(requirements=requirements, seed=4)

    for node in result.nodes:
        assert node.x >= node.radius
        assert node.y >= node.radius
        assert node.x <= result.boundary.width - node.radius
        assert node.y <= result.boundary.height - node.radius


def test_score_graph_layout_front_bonus_for_frontmost_veranda_and_garage() -> None:
    nodes = [
        GraphNode(id="a", name="veranda1", room_type="veranda", radius=5, x=20, y=5),
        GraphNode(id="b", name="garage1", room_type="garage", radius=6, x=50, y=6),
        GraphNode(id="c", name="livingRoom1", room_type="livingRoom", radius=10, x=60, y=30),
    ]
    edges = [GraphEdge(source_id="a", target_id="c", weight=1.2)]
    relations = [
        {"room_type": "veranda", "related_room": ["livingRoom"], "constraint_level": "hard_AND"}
    ]

    score = score_graph_layout(nodes=nodes, edges=edges, relation_constraints=relations)

    assert score.front_bonus == 50.0
    assert score.total_score > 40.0
    assert score.usable_layout is True
